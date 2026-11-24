const progress = document.querySelector("[data-state-url]");
if (progress) {
  const statusBadge = document.querySelector("#run-status");
  const message = document.querySelector("#run-message");
  async function checkState() {
    try {
      const response = await fetch(progress.dataset.stateUrl, { cache: "no-store" });
      if (!response.ok) throw new Error("Unable to read run state");
      const { state, label, message: detail } = await response.json();
      if (state === "complete" || state === "aborted") {
        window.location.reload();
        return;
      }
      if (progress.dataset.state !== state) {
        progress.dataset.state = state;
        statusBadge.className = "badge " + state;
        statusBadge.textContent = label;
        message.textContent = detail;
      }
    } catch {
      // Retry while the local server reconnects.
    }
    window.setTimeout(checkState, 1500);
  }
  window.setTimeout(checkState, 1500);
}

const filters = document.querySelector(".filters");
if (filters) {
  const cases = [...document.querySelectorAll("[data-result]")];
  const buttons = [...filters.querySelectorAll("[data-filter]")];
  const empty = document.querySelector("#empty-filter");
  filters.hidden = false;
  for (const button of buttons) {
    button.addEventListener("click", () => {
      for (const item of buttons) item.setAttribute("aria-pressed", String(item === button));
      for (const row of cases) {
        row.hidden = button.dataset.filter !== "all" && row.dataset.result !== button.dataset.filter;
      }
      empty.hidden = cases.some((row) => !row.hidden);
    });
  }
}

const preview = document.querySelector("#preview");
if (preview && typeof preview.showModal === "function") {
  const title = document.querySelector("#preview-title");
  const image = document.querySelector("#preview-image");
  const error = document.querySelector("#preview-error");
  image.addEventListener("load", () => { image.hidden = false; });
  image.addEventListener("error", () => { error.hidden = false; });
  preview.addEventListener("close", () => { image.removeAttribute("src"); });
  for (const link of document.querySelectorAll("[data-preview]")) {
    link.addEventListener("click", (event) => {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      title.textContent = link.dataset.preview;
      image.alt = title.textContent;
      image.hidden = true;
      error.hidden = true;
      image.src = link.href;
      preview.showModal();
    });
  }
}
