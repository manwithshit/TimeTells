from __future__ import annotations

import argparse
import math
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from PIL import Image
from scipy.spatial import Delaunay


REPO_ROOT = Path(__file__).resolve().parents[1]
ANCHOR_DIR = REPO_ROOT / "content" / "anchors" / "natural"
FRAME_DIR = REPO_ROOT / "web" / "assets" / "frames"

ANCHOR_AGES = (0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 80)
OUTPUT_AGES = tuple(range(0, 81))
SIZE = 768
EYE_DISTANCE = 160.0
EYE_Y = SIZE * 0.52

LEFT_EYE = (33, 133, 159, 145)
RIGHT_EYE = (362, 263, 386, 374)
LEFT_EAR = (234, 127, 162, 21, 54, 103, 93, 132, 58)
RIGHT_EAR = (454, 356, 389, 251, 284, 332, 323, 361, 288)
EAR_TRAVEL = 0.45
BROW = (70, 63, 105, 66, 107, 336, 296, 334, 293, 300)
OUTER_LIPS = (
    61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291, 375, 321, 405, 314, 17, 84, 181, 91, 146,
)
INNER_MOUTH = (
    78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95,
)
ALIGN_LANDMARKS = (33, 133, 159, 145, 362, 263, 386, 374, 1, 4)
SILHOUETTE_SAMPLES = 72


def read_rgba(path: Path) -> np.ndarray:
    return np.array(Image.open(path).convert("RGBA"))


def composite_white(rgba: np.ndarray) -> np.ndarray:
    alpha = rgba[:, :, 3:4].astype(np.float32) / 255.0
    return np.clip(rgba[:, :, :3] * alpha + 255.0 * (1.0 - alpha), 0, 255).astype(np.uint8)


def detect_landmarks(mesh: object, rgba: np.ndarray) -> np.ndarray:
    result = mesh.process(composite_white(rgba))
    if not result.multi_face_landmarks:
        raise RuntimeError("MediaPipe could not detect a face")
    height, width = rgba.shape[:2]
    return np.array(
        [(item.x * width, item.y * height) for item in result.multi_face_landmarks[0].landmark],
        dtype=np.float32,
    )


def eye_centers(points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    eyes = [points[list(LEFT_EYE)].mean(axis=0), points[list(RIGHT_EYE)].mean(axis=0)]
    eyes.sort(key=lambda point: float(point[0]))
    return eyes[0], eyes[1]


def canonical_transform(points: np.ndarray) -> np.ndarray:
    left, right = eye_centers(points)
    midpoint = (left + right) / 2.0
    delta = right - left
    distance = float(np.linalg.norm(delta))
    angle = math.atan2(float(delta[1]), float(delta[0]))
    scale = EYE_DISTANCE / distance
    cosine = math.cos(angle) * scale
    sine = math.sin(angle) * scale
    matrix = np.array([[cosine, sine], [-sine, cosine]], dtype=np.float32)
    translation = np.array((SIZE * 0.5, EYE_Y), dtype=np.float32) - matrix @ midpoint
    return np.hstack((matrix, translation.reshape(2, 1)))


def transform_points(points: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    homogeneous = np.concatenate((points, np.ones((len(points), 1), dtype=np.float32)), axis=1)
    return homogeneous @ matrix.T


def global_align(rgba: np.ndarray, points: np.ndarray, target: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    matrix, _ = cv2.estimateAffinePartial2D(
        points[list(ALIGN_LANDMARKS)],
        target[list(ALIGN_LANDMARKS)],
        method=cv2.LMEDS,
    )
    if matrix is None:
        raise RuntimeError("Could not estimate the canonical face transform")
    aligned = cv2.warpAffine(
        rgba,
        matrix,
        (SIZE, SIZE),
        flags=cv2.INTER_LANCZOS4,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0, 0),
    )
    return aligned, transform_points(points, matrix)


def face_oval_indices() -> list[int]:
    connections = mp.solutions.face_mesh.FACEMESH_FACE_OVAL
    return sorted({index for edge in connections for index in edge})


def largest_component(binary: np.ndarray) -> np.ndarray:
    count, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    if count <= 1:
        return binary
    largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return (labels == largest).astype(np.uint8)


def warp_triangle(
    source: np.ndarray,
    target: np.ndarray,
    coverage: np.ndarray,
    source_triangle: np.ndarray,
    target_triangle: np.ndarray,
) -> None:
    source_rect = cv2.boundingRect(np.float32(source_triangle))
    target_rect = cv2.boundingRect(np.float32(target_triangle))
    sx, sy, sw, sh = source_rect
    tx, ty, tw, th = target_rect
    if min(sw, sh, tw, th) <= 1:
        return
    source_local = source_triangle - np.array((sx, sy), dtype=np.float32)
    target_local = target_triangle - np.array((tx, ty), dtype=np.float32)
    source_crop = source[sy : sy + sh, sx : sx + sw]
    if source_crop.size == 0:
        return
    matrix = cv2.getAffineTransform(source_local.astype(np.float32), target_local.astype(np.float32))
    warped = cv2.warpAffine(
        source_crop,
        matrix,
        (tw, th),
        flags=cv2.INTER_LANCZOS4,
        borderMode=cv2.BORDER_REFLECT_101,
    )
    triangle_mask = np.zeros((th, tw), dtype=np.float32)
    cv2.fillConvexPoly(triangle_mask, np.int32(np.round(target_local)), 1.0, lineType=cv2.LINE_AA)
    triangle_mask = triangle_mask[:, :, None]
    target_roi = target[ty : ty + th, tx : tx + tw]
    coverage_roi = coverage[ty : ty + th, tx : tx + tw]
    np.multiply(target_roi, 1.0 - triangle_mask, out=target_roi)
    target_roi += warped.astype(np.float32) * triangle_mask
    np.maximum(coverage_roi, triangle_mask[:, :, 0], out=coverage_roi)


def silhouette_samples(alpha: np.ndarray, count: int = SILHOUETTE_SAMPLES) -> np.ndarray:
    binary = largest_component((alpha >= 128).astype(np.uint8))
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not contours:
        return np.zeros((0, 2), dtype=np.float32)
    contour = max(contours, key=cv2.contourArea).reshape(-1, 2).astype(np.float32)
    center = contour.mean(axis=0)
    angles = np.arctan2(contour[:, 1] - center[1], contour[:, 0] - center[0])
    targets = np.linspace(-math.pi, math.pi, count, endpoint=False)
    samples = np.zeros((count, 2), dtype=np.float32)
    half_bin = math.pi / count
    for index, target in enumerate(targets):
        delta = (angles - target + math.pi) % (2 * math.pi) - math.pi
        nearby = np.abs(delta) <= half_bin
        if np.any(nearby):
            subset = contour[nearby]
            radius = np.linalg.norm(subset - center, axis=1)
            samples[index] = subset[int(np.argmax(radius))]
        else:
            samples[index] = contour[int(np.argmin(np.abs(delta)))]
    return samples


def morph_control_points(points: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    mesh = points[:468].astype(np.float32)
    outline = silhouette_samples(alpha)
    corners = np.array(
        ((0.0, 0.0), (SIZE - 1.0, 0.0), (SIZE - 1.0, SIZE - 1.0), (0.0, SIZE - 1.0)),
        dtype=np.float32,
    )
    return np.vstack((mesh, outline, corners))


def warp_image(source: np.ndarray, source_points: np.ndarray, target_points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    channels = source.shape[2] if source.ndim == 3 else 1
    output = np.zeros((SIZE, SIZE, channels), dtype=np.float32)
    coverage = np.zeros((SIZE, SIZE), dtype=np.float32)
    triangulation = Delaunay(target_points)
    for simplex in triangulation.simplices:
        warp_triangle(source, output, coverage, source_points[simplex], target_points[simplex])
    return np.clip(output, 0, 255).astype(np.uint8), coverage


def mouth_interior_mask(points: np.ndarray) -> np.ndarray:
    mask = np.zeros((SIZE, SIZE), dtype=np.uint8)
    polygon = np.round(points[list(INNER_MOUTH)]).astype(np.int32)
    cv2.fillPoly(mask, [polygon], 255, lineType=cv2.LINE_AA)
    return cv2.erode(mask, np.ones((3, 3), np.uint8), iterations=1)


def transfer_teeth(
    donor: np.ndarray,
    donor_points: np.ndarray,
    target: np.ndarray,
    target_points: np.ndarray,
) -> np.ndarray:
    donor_ctrl = morph_control_points(donor_points, donor[:, :, 3])
    target_ctrl = morph_control_points(target_points, target[:, :, 3])
    warped, coverage = warp_image(donor, donor_ctrl, target_ctrl)
    inner = cv2.dilate(mouth_interior_mask(target_points), np.ones((7, 7), np.uint8))
    weight = cv2.GaussianBlur(inner.astype(np.float32), (0, 0), sigmaX=1.4, sigmaY=1.4) / 255.0
    weight = np.clip(weight * np.clip(coverage, 0.0, 1.0), 0.0, 1.0)[:, :, None]
    rgb = target[:, :, :3].astype(np.float32) * (1.0 - weight) + warped[:, :, :3].astype(np.float32) * weight
    return np.dstack((np.clip(rgb, 0, 255).astype(np.uint8), target[:, :, 3]))


def _feature_punch(points: np.ndarray) -> np.ndarray:
    punch = np.zeros((SIZE, SIZE), dtype=np.uint8)
    left, right = eye_centers(points)
    eye_distance = float(np.linalg.norm(right - left))
    for center in (left, right):
        cv2.ellipse(
            punch,
            tuple(np.int32(np.round(center))),
            (int(eye_distance * 0.22), int(eye_distance * 0.14)),
            0,
            0,
            360,
            255,
            -1,
            lineType=cv2.LINE_AA,
        )
    cv2.fillPoly(punch, [np.round(points[list(INNER_MOUTH)]).astype(np.int32)], 255)
    return punch


def visible_skin_mask(rgba: np.ndarray, points: np.ndarray) -> np.ndarray:
    subject = (rgba[:, :, 3] > 140).astype(np.uint8)
    lab = cv2.cvtColor(rgba[:, :, :3], cv2.COLOR_RGB2LAB)
    lightness = lab[:, :, 0].astype(np.float32)
    chroma = np.hypot(lab[:, :, 1].astype(np.float32) - 128.0, lab[:, :, 2].astype(np.float32) - 128.0)
    dark_hair = (lightness < 82.0) & (chroma < 24.0)
    gray_hair = (chroma < 7.0) & (lightness > 90.0) & (lightness < 220.0)
    hair = dark_hair | gray_hair
    skin = (subject > 0) & (~hair) & (lightness > 70.0) & (lightness < 250.0) & (chroma < 62.0)
    skin = skin & (_feature_punch(points) == 0)
    binary = largest_component(skin.astype(np.uint8))
    return cv2.GaussianBlur(binary.astype(np.float32), (0, 0), sigmaX=8.0, sigmaY=8.0)


def face_skin_mask(rgba: np.ndarray, points: np.ndarray) -> np.ndarray:
    mask = np.zeros((SIZE, SIZE), dtype=np.uint8)
    oval = cv2.convexHull(points[np.array(face_oval_indices())].astype(np.int32))
    cv2.fillConvexPoly(mask, oval, 255, lineType=cv2.LINE_AA)
    mask = cv2.erode(mask, np.ones((15, 15), np.uint8))
    left, right = eye_centers(points)
    eye_distance = float(np.linalg.norm(right - left))
    for center in (left, right):
        cv2.ellipse(
            mask,
            tuple(np.int32(np.round(center))),
            (int(eye_distance * 0.28), int(eye_distance * 0.18)),
            0,
            0,
            360,
            0,
            -1,
            lineType=cv2.LINE_AA,
        )
    for index in BROW:
        cv2.circle(mask, tuple(np.int32(np.round(points[index]))), 14, 0, -1, lineType=cv2.LINE_AA)
    cv2.fillPoly(mask, [np.round(points[list(OUTER_LIPS)]).astype(np.int32)], 0, lineType=cv2.LINE_AA)
    cv2.ellipse(mask, tuple(np.int32(np.round(points[1]))), (28, 36), 0, 0, 360, 0, -1, cv2.LINE_AA)
    lab = cv2.cvtColor(rgba[:, :, :3], cv2.COLOR_RGB2LAB)
    lightness = lab[:, :, 0].astype(np.float32)
    chroma = np.hypot(lab[:, :, 1].astype(np.float32) - 128.0, lab[:, :, 2].astype(np.float32) - 128.0)
    skin = (mask > 0) & (rgba[:, :, 3] > 200) & (lightness > 95) & (lightness < 225) & (chroma > 8) & (chroma < 48)
    return skin.astype(np.float32)


def skin_lab_mean(rgba: np.ndarray, points: np.ndarray) -> np.ndarray:
    mask = face_skin_mask(rgba, points) > 0.5
    if not np.any(mask):
        raise RuntimeError("No skin pixels for color match")
    lab = cv2.cvtColor(rgba[:, :, :3], cv2.COLOR_RGB2LAB).astype(np.float32)
    return np.median(lab[mask], axis=0)


def outer_cheek_mask(points: np.ndarray) -> np.ndarray:
    left, right = eye_centers(points)
    eye_distance = float(np.linalg.norm(right - left))
    mask = np.zeros((SIZE, SIZE), dtype=np.uint8)
    radius = (
        max(14, int(round(eye_distance * 0.13))),
        max(12, int(round(eye_distance * 0.12))),
    )
    for center, side in ((left, -1.0), (right, 1.0)):
        sample = center + np.array((side * eye_distance * 0.20, eye_distance * 0.36), dtype=np.float32)
        cv2.ellipse(
            mask,
            tuple(np.int32(np.round(sample))),
            radius,
            0,
            0,
            360,
            255,
            -1,
            lineType=cv2.LINE_AA,
        )
    return mask


def forehead_region_mask(points: np.ndarray) -> np.ndarray:
    left, right = eye_centers(points)
    mid = (left + right) / 2.0
    eye_distance = float(np.linalg.norm(right - left))
    brow_y = float(np.mean(points[list(BROW), 1])) if len(points) > max(BROW) else SIZE * 0.44
    top_y = float(points[10, 1]) if len(points) > 10 else SIZE * 0.28
    mask = np.zeros((SIZE, SIZE), dtype=np.uint8)
    cv2.ellipse(
        mask,
        (int(round(mid[0])), int(round((top_y + brow_y) / 2.0))),
        (max(48, int(round(eye_distance * 0.90))), max(28, int(round((brow_y - top_y) * 0.58 + 16.0)))),
        0,
        0,
        360,
        255,
        -1,
        lineType=cv2.LINE_AA,
    )
    cv2.ellipse(
        mask,
        (int(round(mid[0])), int(round(top_y - 52.0))),
        (max(36, int(round(eye_distance * 0.70))), 96),
        0,
        0,
        360,
        255,
        -1,
        lineType=cv2.LINE_AA,
    )
    mask[int(np.floor(brow_y - 2.0)) :, :] = 0
    return cv2.GaussianBlur(mask.astype(np.float32), (0, 0), sigmaX=7.0, sigmaY=7.0) / 255.0


def even_forehead_to_cheeks(rgba: np.ndarray, points: np.ndarray) -> np.ndarray:
    skin = np.clip(visible_skin_mask(rgba, points), 0.0, 1.0)
    if float(skin.max()) < 0.2:
        return rgba
    left, right = eye_centers(points)
    mid_x = int(round(float((left[0] + right[0]) / 2.0)))
    top_y = int(round(float(points[10, 1]))) if len(points) > 10 else int(SIZE * 0.28)
    brow_y = int(round(float(np.mean(points[list(BROW), 1])))) if len(points) > max(BROW) else int(SIZE * 0.44)
    ys = slice(max(0, top_y + 14), max(top_y + 24, brow_y - 18))
    xs = slice(max(0, mid_x - 26), min(SIZE, mid_x + 26))
    sample = skin[ys, xs] > 0.55
    cheeks = (outer_cheek_mask(points) > 0) & (skin > 0.55)
    if int(sample.sum()) < 80 or not np.any(cheeks):
        return rgba
    lab = cv2.cvtColor(rgba[:, :, :3], cv2.COLOR_RGB2LAB).astype(np.float32)
    forehead_mean = np.median(lab[ys, xs][sample], axis=0)
    cheek_mean = np.median(lab[cheeks], axis=0)
    delta_l = float(cheek_mean[0] - forehead_mean[0])
    if delta_l > -6.0:
        return rgba
    shift = np.array(
        (
            float(np.clip(delta_l, -28.0, -6.0)),
            float(np.clip(cheek_mean[1] - forehead_mean[1], -8.0, 8.0)),
            float(np.clip(cheek_mean[2] - forehead_mean[2], -8.0, 8.0)),
        ),
        dtype=np.float32,
    )
    region = np.clip(forehead_region_mask(points) * skin, 0.0, 1.0)
    if float(region.max()) < 0.2:
        return rgba
    low = cv2.GaussianBlur(lab, (0, 0), sigmaX=6.0, sigmaY=6.0)
    high = lab - low
    low = low + shift[None, None, :] * region[:, :, None]
    out = np.clip(low + high, 0, 255).astype(np.uint8)
    return np.dstack((cv2.cvtColor(out, cv2.COLOR_LAB2RGB), rgba[:, :, 3]))


def unify_skin_tone(rgba: np.ndarray, points: np.ndarray, target_mean: np.ndarray) -> np.ndarray:
    weight = np.clip(visible_skin_mask(rgba, points), 0.0, 1.0)
    if float(weight.max()) < 0.05:
        return rgba
    lab = cv2.cvtColor(rgba[:, :, :3], cv2.COLOR_RGB2LAB).astype(np.float32)
    active = weight > 0.35
    if not np.any(active):
        return rgba
    current = np.average(lab[active], axis=0, weights=weight[active])
    shift = (target_mean - current) * np.array((0.9, 0.88, 0.88), dtype=np.float32)
    low = cv2.GaussianBlur(lab, (0, 0), sigmaX=9.0, sigmaY=9.0)
    high = lab - low
    low = low + shift[None, None, :] * weight[:, :, None]
    out = np.clip(low + high, 0, 255).astype(np.uint8)
    unified = np.dstack((cv2.cvtColor(out, cv2.COLOR_LAB2RGB), rgba[:, :, 3]))
    return even_forehead_to_cheeks(unified, points)


def cut_below_jaw(binary: np.ndarray, points: np.ndarray, age: int | None = None) -> np.ndarray:
    visible = np.where(binary > 0)[0]
    if visible.size == 0:
        return binary
    chin_y = float(points[152, 1])
    below = float(visible.max()) - chin_y
    if below <= 8:
        return binary
    if age is not None and age < 16 and below <= 24:
        return binary
    mouth_y = float(((points[13] + points[14]) / 2.0)[1])
    oval = points[np.array(face_oval_indices())]
    jaw = oval[oval[:, 1] >= mouth_y - 24]
    if len(jaw) < 4:
        limit = chin_y + 18
        return binary & (np.arange(SIZE)[:, None] <= limit).astype(np.uint8)
    jaw = jaw[np.argsort(jaw[:, 0])]
    xs = [float(jaw[0, 0])]
    ys = [float(jaw[0, 1])]
    for x, y in jaw[1:]:
        if x > xs[-1] + 0.5:
            xs.append(float(x))
            ys.append(float(y))
    cut_y = np.interp(np.arange(SIZE, dtype=np.float32), np.array(xs), np.array(ys), left=ys[0], right=ys[-1])
    cut_y = np.minimum(cut_y + 8.0, chin_y + 12.0)
    keep = np.arange(SIZE)[:, None] <= cut_y[None, :]
    return binary & keep.astype(np.uint8)


def edge_white_background(rgb: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    floor = rgb.min(axis=2)
    saturation = rgb.max(axis=2) - floor
    paper = ((alpha >= 200) & (floor > 236) & (saturation < 14)).astype(np.uint8)
    vacant = (alpha < 96).astype(np.uint8)
    touch = cv2.dilate(vacant, np.ones((3, 3), np.uint8)) & paper
    height, width = paper.shape
    work = paper * 255
    background = vacant.copy()
    ys, xs = np.where(touch > 0)
    for x, y in zip(xs.tolist(), ys.tolist()):
        if work[y, x] == 0:
            continue
        fill = np.zeros((height + 2, width + 2), dtype=np.uint8)
        cv2.floodFill(work, fill, (int(x), int(y)), 128)
        background |= (work == 128).astype(np.uint8)
        work[work == 128] = 0
    return background


def hard_crop_alpha(aligned: np.ndarray, points: np.ndarray, age: int | None = None) -> np.ndarray:
    rgb = aligned[:, :, :3].astype(np.float32)
    alpha = aligned[:, :, 3]
    background = edge_white_background(rgb, alpha)
    subject = (alpha >= 96) & (background == 0)
    binary = largest_component(subject.astype(np.uint8))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    binary = largest_component(binary)
    binary = cut_below_jaw(binary, points, age)
    distance = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
    return np.clip(distance, 0.0, 1.0)


def apply_hard_crop(rgba: np.ndarray, points: np.ndarray, age: int | None = None) -> np.ndarray:
    alpha = hard_crop_alpha(rgba, points, age)
    return np.dstack((rgba[:, :, :3], np.round(alpha * 255).astype(np.uint8)))


def harden_alpha(alpha: np.ndarray) -> np.ndarray:
    binary = largest_component((alpha >= 128).astype(np.uint8))
    distance = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
    return np.clip(distance, 0.0, 1.0)


def to_linear(rgb: np.ndarray) -> np.ndarray:
    value = rgb.astype(np.float32) / 255.0
    return np.where(value <= 0.04045, value / 12.92, ((value + 0.055) / 1.055) ** 2.4)


def from_linear(value: np.ndarray) -> np.ndarray:
    srgb = np.where(value <= 0.0031308, value * 12.92, 1.055 * np.power(value, 1.0 / 2.4) - 0.055)
    return np.clip(srgb * 255.0, 0, 255).astype(np.uint8)


def interpolate(start: np.ndarray, end: np.ndarray, amount: float) -> np.ndarray:
    if amount <= 0:
        return start
    if amount >= 1:
        return end
    start_rgb = to_linear(start[:, :, :3])
    end_rgb = to_linear(end[:, :, :3])
    rgb = from_linear(start_rgb * (1.0 - amount) + end_rgb * amount)
    mixed_alpha = start[:, :, 3].astype(np.float32) * (1.0 - amount) + end[:, :, 3].astype(np.float32) * amount
    alpha = np.round(harden_alpha(mixed_alpha) * 255).astype(np.uint8)
    return np.dstack((rgb, alpha))


def ear_hold_mask(points: np.ndarray) -> np.ndarray:
    mask = np.zeros((SIZE, SIZE), dtype=np.uint8)
    left_eye, right_eye = eye_centers(points)
    eye_distance = float(np.linalg.norm(right_eye - left_eye))
    axes = (max(36, int(round(eye_distance * 0.46))), max(52, int(round(eye_distance * 0.66))))
    midpoint = (left_eye + right_eye) / 2.0
    for cluster in (LEFT_EAR, RIGHT_EAR):
        center = points[list(cluster)].mean(axis=0)
        outward = center - midpoint
        length = float(np.linalg.norm(outward))
        if length > 1:
            center = center + outward / length * 16.0
        cv2.ellipse(
            mask,
            tuple(np.int32(np.round(center))),
            axes,
            0,
            0,
            360,
            255,
            -1,
            lineType=cv2.LINE_AA,
        )
    mask = cv2.dilate(mask, np.ones((17, 17), np.uint8))
    return cv2.GaussianBlur(mask, (0, 0), sigmaX=4.2, sigmaY=4.2).astype(np.float32) / 255.0


def dampen_ear_targets(start_ctrl: np.ndarray, end_ctrl: np.ndarray, mid_ctrl: np.ndarray, amount: float) -> np.ndarray:
    adjusted = mid_ctrl.copy()
    indices = np.array(LEFT_EAR + RIGHT_EAR, dtype=np.int32)
    travel = amount * EAR_TRAVEL
    adjusted[indices] = start_ctrl[indices] * (1.0 - travel) + end_ctrl[indices] * travel
    return adjusted


def interpolate_morphed(
    start: np.ndarray,
    end: np.ndarray,
    start_points: np.ndarray,
    end_points: np.ndarray,
    amount: float,
) -> np.ndarray:
    if amount <= 0:
        return start
    if amount >= 1:
        return end
    start_ctrl = morph_control_points(start_points, start[:, :, 3])
    end_ctrl = morph_control_points(end_points, end[:, :, 3])
    mid_ctrl = start_ctrl * (1.0 - amount) + end_ctrl * amount
    mid_ctrl = dampen_ear_targets(start_ctrl, end_ctrl, mid_ctrl, amount)
    start_warped, start_coverage = warp_image(start, start_ctrl, mid_ctrl)
    end_warped, end_coverage = warp_image(end, end_ctrl, mid_ctrl)
    warped = interpolate(start_warped, end_warped, amount)
    nearer_warped = start_warped if amount < 0.5 else end_warped
    coverage = np.minimum(start_coverage, end_coverage)
    coverage = cv2.GaussianBlur(coverage, (0, 0), sigmaX=0.8, sigmaY=0.8)
    coverage = np.clip(coverage, 0.0, 1.0)[:, :, None]
    rgb = warped[:, :, :3].astype(np.float32) * coverage + nearer_warped[:, :, :3].astype(np.float32) * (1.0 - coverage)
    nearer_src = start if amount < 0.5 else end
    nearer_pts = start_points if amount < 0.5 else end_points
    ear = np.clip(
        ear_hold_mask(start_points) + ear_hold_mask(end_points) + ear_hold_mask(mid_ctrl[:468]),
        0.0,
        1.0,
    )[:, :, None]
    teeth = cv2.dilate(mouth_interior_mask(nearer_pts), np.ones((3, 3), np.uint8))
    teeth = (cv2.GaussianBlur(teeth.astype(np.float32), (0, 0), sigmaX=0.8, sigmaY=0.8) / 255.0)[:, :, None]
    rgb = rgb * (1.0 - ear) + nearer_warped[:, :, :3].astype(np.float32) * ear
    rgb = rgb * (1.0 - teeth) + nearer_src[:, :, :3].astype(np.float32) * teeth
    return np.dstack((np.clip(rgb, 0, 255).astype(np.uint8), nearer_src[:, :, 3]))


def surrounding_anchors(age: int, anchors: dict[int, np.ndarray]) -> tuple[int, int]:
    ages = sorted(anchors)
    if age <= ages[0]:
        return ages[0], ages[0]
    if age >= ages[-1]:
        return ages[-1], ages[-1]
    start = max(item for item in ages if item <= age)
    end = min(item for item in ages if item >= age)
    return start, end


def write_frames(anchors: dict[int, np.ndarray], points: dict[int, np.ndarray]) -> None:
    FRAME_DIR.mkdir(parents=True, exist_ok=True)
    for age in OUTPUT_AGES:
        start_age, end_age = surrounding_anchors(age, anchors)
        if start_age == end_age:
            frame = anchors[start_age]
            frame_points = points[start_age]
        else:
            amount = (age - start_age) / (end_age - start_age)
            frame = interpolate_morphed(
                anchors[start_age],
                anchors[end_age],
                points[start_age],
                points[end_age],
                amount,
            )
            frame_points = points[start_age] * (1.0 - amount) + points[end_age] * amount
        if age > 10:
            frame = even_forehead_to_cheeks(frame, frame_points)
        Image.fromarray(frame).save(FRAME_DIR / f"age-{age:03d}.webp", "WEBP", lossless=True, method=6)


def required_anchor_paths() -> dict[int, Path]:
    return {age: ANCHOR_DIR / f"age-{age:03d}.webp" for age in ANCHOR_AGES}


def missing_anchors() -> list[Path]:
    return [path for path in required_anchor_paths().values() if not path.exists()]


def build_sequence() -> None:
    missing = missing_anchors()
    if missing:
        names = ", ".join(path.name for path in missing)
        raise FileNotFoundError(
            f"Need all {len(ANCHOR_AGES)} anchors in {ANCHOR_DIR}. Missing: {names}"
        )
    anchor_rgba = {age: read_rgba(path) for age, path in required_anchor_paths().items()}
    with mp.solutions.face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
    ) as mesh:
        original_points = {age: detect_landmarks(mesh, rgba) for age, rgba in anchor_rgba.items()}
        reference_age = 30 if 30 in original_points else sorted(original_points)[len(original_points) // 2]
        canonical_matrix = canonical_transform(original_points[reference_age])
        target_points = transform_points(original_points[reference_age], canonical_matrix)
        prepared: dict[int, np.ndarray] = {}
        prepared_points: dict[int, np.ndarray] = {}
        for age in ANCHOR_AGES:
            aligned, aligned_points = global_align(anchor_rgba[age], original_points[age], target_points)
            prepared[age] = apply_hard_crop(aligned, aligned_points, age)
            prepared_points[age] = aligned_points
        if 20 in prepared and 30 in prepared:
            prepared[30] = transfer_teeth(prepared[20], prepared_points[20], prepared[30], prepared_points[30])
        if 10 in prepared:
            reference = skin_lab_mean(prepared[10], prepared_points[10])
            for age in ANCHOR_AGES:
                if age > 10:
                    prepared[age] = unify_skin_tone(prepared[age], prepared_points[age], reference)
        write_frames(prepared, prepared_points)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Align 16 natural-track anchors and write 0–80 web frames.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only list missing anchors; do not process.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.check:
        missing = missing_anchors()
        if missing:
            print("missing:")
            for path in missing:
                print(f"  {path}")
            raise SystemExit(1)
        print(f"ok: {len(ANCHOR_AGES)} anchors in {ANCHOR_DIR}")
        return
    build_sequence()
    print(f"wrote {len(OUTPUT_AGES)} frames to {FRAME_DIR}")


if __name__ == "__main__":
    main()
