// Confirmación para formularios con data-confirm (acciones que cambian estado).
document.addEventListener("submit", (event) => {
  const form = event.target;
  const message = form.dataset ? form.dataset.confirm : null;
  if (message && !window.confirm(message)) {
    event.preventDefault();
  }
});

// Evita envíos dobles deshabilitando el botón al enviar.
document.addEventListener("submit", (event) => {
  if (event.defaultPrevented) return;
  const button = event.submitter;
  if (button && !button.hasAttribute("data-allow-double")) {
    setTimeout(() => { button.disabled = true; }, 0);
  }
});
