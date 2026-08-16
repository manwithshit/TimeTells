const PX_PER_YEAR = 10;

const slider = document.querySelector("#ageSlider");
const ageLabel = document.querySelector("#age");
const portrait = document.querySelector("#portrait");
const rulerTrack = document.querySelector("#rulerTrack");
const rulerWindow = document.querySelector("#rulerWindow");

const params = new URLSearchParams(location.search);
const requestedAge = params.has("age") ? Number(params.get("age")) : null;

if (requestedAge !== null && Number.isFinite(requestedAge)) {
  slider.value = String(Math.min(80, Math.max(0, requestedAge)));
} else {
  slider.value = "0";
}

function sourceFor(age) {
  return `assets/frames/age-${String(age).padStart(3, "0")}.webp?v=1`;
}

function setAge(age) {
  const next = String(Math.min(80, Math.max(0, Math.round(age))));
  if (next === slider.value) return;
  slider.value = next;
  render();
}

for (let age = 0; age <= 80; age += 1) {
  const tick = document.createElement("span");
  tick.className = "ruler-tick";
  if (age % 10 === 0) tick.classList.add("is-ten");
  else if (age % 5 === 0) tick.classList.add("is-five");
  rulerTrack.append(tick);
}

function render() {
  const age = Math.round(Number(slider.value));
  portrait.src = sourceFor(age);
  ageLabel.textContent = age === 0 ? "Baby" : `Age: ${age}`;
  rulerTrack.style.setProperty("--age", String(age));
}

slider.addEventListener("input", render);

let drag = null;
rulerWindow.addEventListener("pointerdown", (event) => {
  if (event.button !== 0) return;
  drag = { x: event.clientX, age: Number(slider.value) };
  rulerWindow.setPointerCapture(event.pointerId);
});
rulerWindow.addEventListener("pointermove", (event) => {
  if (!drag) return;
  setAge(drag.age + (drag.x - event.clientX) / PX_PER_YEAR);
});
const endDrag = () => {
  drag = null;
};
rulerWindow.addEventListener("pointerup", endDrag);
rulerWindow.addEventListener("pointercancel", endDrag);

window.addEventListener("keydown", (event) => {
  if (event.key === "ArrowLeft") {
    event.preventDefault();
    setAge(Number(slider.value) - 1);
  }
  if (event.key === "ArrowRight") {
    event.preventDefault();
    setAge(Number(slider.value) + 1);
  }
});

if (!params.has("shot")) {
  for (let age = 0; age <= 80; age += 1) {
    const image = new Image();
    image.src = sourceFor(age);
  }
}

render();
