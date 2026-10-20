// Partidas dinámicas de cotización. El cálculo aquí es solo una estimación visual;
// el servidor valida precios y recalcula todos los importes al guardar.
(() => {
  "use strict";
  const body = document.getElementById("items-body");
  const template = document.getElementById("item-template");
  const total = document.getElementById("id_items-TOTAL_FORMS");
  const prices = JSON.parse(document.getElementById("product-prices").textContent || "{}");
  const estimate = document.getElementById("estimate");
  const fmt = new Intl.NumberFormat("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const num = (v) => (v === "" || v == null || Number.isNaN(Number(v)) ? null : Number(v));

  function recalc() {
    let sum = 0;
    body.querySelectorAll(".item-row").forEach((row) => {
      if (row.classList.contains("d-none")) return;
      const product = row.querySelector("select[name$='-product']");
      const qty = num(row.querySelector("input[name$='-quantity']").value);
      const priceInput = row.querySelector("input[name$='-unit_price']");
      const ref = prices[product.value] || "";
      priceInput.placeholder = ref ? `Ref. ${ref}` : "";
      const price = num(priceInput.value) ?? num(ref);
      const disc = num(row.querySelector("input[name$='-discount_pct']").value) || 0;
      const cell = row.querySelector(".line-total");
      if (qty == null || price == null) { cell.textContent = "—"; return; }
      const line = qty * price * (1 - disc / 100);
      sum += line;
      cell.textContent = `$${fmt.format(line)}`;
    });
    estimate.textContent = `$${fmt.format(sum)}`;
  }

  document.getElementById("add-item").addEventListener("click", () => {
    const index = Number(total.value);
    const html = template.innerHTML.replaceAll("__prefix__", String(index));
    body.insertAdjacentHTML("beforeend", html);
    total.value = String(index + 1);
    recalc();
  });

  body.addEventListener("click", (event) => {
    const button = event.target.closest(".remove-item");
    if (!button) return;
    const row = button.closest(".item-row");
    row.querySelector("input[name$='-DELETE']").checked = true;
    row.classList.add("d-none");
    row.querySelectorAll("select, input:not([type=checkbox])").forEach((el) => { el.required = false; });
    recalc();
  });
  body.addEventListener("input", recalc);
  body.addEventListener("change", recalc);
  recalc();
})();
