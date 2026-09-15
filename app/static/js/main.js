/* Plataforma comercial Remsa · interacciones del sitio */
(function () {
  'use strict';

  const CART_KEY = 'remsa_cotizacion';
  const $ = (sel, ctx = document) => ctx.querySelector(sel);
  const $$ = (sel, ctx = document) => Array.from(ctx.querySelectorAll(sel));

  /* ---------- carrito de cotización (localStorage) ---------- */
  const cart = {
    read() {
      try { return JSON.parse(localStorage.getItem(CART_KEY)) || []; } catch (e) { return []; }
    },
    write(items) {
      localStorage.setItem(CART_KEY, JSON.stringify(items));
      cart.refreshBadge();
      document.dispatchEvent(new CustomEvent('cart:change'));
    },
    add(item) {
      const items = cart.read();
      const found = items.find((i) => i.product_slug === item.product_slug && i.model === item.model && i.color === item.color);
      if (found) { found.quantity += item.quantity; } else { items.push(item); }
      cart.write(items);
    },
    remove(index) {
      const items = cart.read();
      items.splice(index, 1);
      cart.write(items);
    },
    clear() { cart.write([]); },
    refreshBadge() {
      const badge = $('#cart-count');
      if (badge) badge.textContent = cart.read().length;
    }
  };
  cart.refreshBadge();

  function toast(message, ok = true) {
    let el = $('#toast');
    if (!el) {
      el = document.createElement('div');
      el.id = 'toast';
      el.style.cssText = 'position:fixed;left:50%;bottom:26px;transform:translateX(-50%) translateY(20px);z-index:200;' +
        'background:#10243d;color:#fff;padding:.8rem 1.2rem;border-radius:12px;font-weight:600;font-size:.9rem;' +
        'box-shadow:0 20px 40px -18px rgba(8,26,46,.8);opacity:0;transition:all .3s ease;max-width:90vw;text-align:center';
      document.body.appendChild(el);
    }
    el.textContent = message;
    el.style.background = ok ? '#10243d' : '#c22e26';
    requestAnimationFrame(() => { el.style.opacity = '1'; el.style.transform = 'translateX(-50%) translateY(0)'; });
    clearTimeout(el._t);
    el._t = setTimeout(() => { el.style.opacity = '0'; el.style.transform = 'translateX(-50%) translateY(20px)'; }, 3200);
  }

  /* ---------- header: menú móvil, scroll, buscador ---------- */
  const header = $('#header');
  window.addEventListener('scroll', () => {
    if (header) header.classList.toggle('is-scrolled', window.scrollY > 8);
  }, { passive: true });

  const burger = $('#burger');
  if (burger) burger.addEventListener('click', () => $('#nav').classList.toggle('is-open'));

  $$('.nav__dropdown > a').forEach((link) => {
    link.addEventListener('click', (event) => {
      if (window.innerWidth <= 860) {
        event.preventDefault();
        link.parentElement.classList.toggle('is-open');
      }
    });
  });

  const searchToggle = $('#search-toggle');
  if (searchToggle) {
    searchToggle.addEventListener('click', () => {
      $('#searchbar').classList.toggle('is-open');
      const input = $('#global-search');
      if (input) input.focus();
    });
  }

  const globalSearch = $('#global-search');
  if (globalSearch) {
    let timer;
    globalSearch.addEventListener('input', () => {
      clearTimeout(timer);
      const q = globalSearch.value.trim();
      const box = $('#search-results');
      if (q.length < 2) { box.innerHTML = ''; return; }
      timer = setTimeout(async () => {
        try {
          const res = await fetch('/api/buscar?q=' + encodeURIComponent(q));
          const data = await res.json();
          box.innerHTML = data.length
            ? data.map((p) => `<a href="/producto/${p.slug}"><span><strong>${p.name}</strong> <small>· ${p.category}</small></span><small>${p.capacity}</small></a>`).join('')
            : '<a href="/contacto"><span>Sin coincidencias. ¿Necesitas un envase especial?</span><small>Contáctanos</small></a>';
        } catch (e) { /* silencio */ }
      }, 220);
    });
  }

  /* ---------- agregar al carrito ---------- */
  document.addEventListener('click', (event) => {
    const btn = event.target.closest('.js-add-cart');
    if (!btn) return;
    cart.add({
      product_slug: btn.dataset.slug,
      product_name: btn.dataset.name,
      image: btn.dataset.image,
      model: btn.dataset.model || '',
      color: '',
      quantity: 1000,
      notes: ''
    });
    toast('Producto agregado a tu cotización');
  });

  const detailBtn = $('.js-add-cart-detail');
  if (detailBtn) {
    detailBtn.addEventListener('click', () => {
      const qty = parseInt($('#qty-input').value, 10);
      if (!qty || qty < 1) { $('#add-feedback').textContent = 'Indica una cantidad válida.'; $('#add-feedback').className = 'form-feedback is-error'; return; }
      cart.add({
        product_slug: detailBtn.dataset.slug,
        product_name: detailBtn.dataset.name,
        image: detailBtn.dataset.image,
        model: $('#variant-select') ? $('#variant-select').value : '',
        color: $('#color-select') ? $('#color-select').value : '',
        quantity: qty,
        notes: $('#notes-input') ? $('#notes-input').value : ''
      });
      const fb = $('#add-feedback');
      fb.className = 'form-feedback is-ok';
      fb.innerHTML = 'Agregado. <a href="/cotizacion">Ir a mi cotización →</a>';
      toast('Producto agregado a tu cotización');
    });
  }

  /* ---------- ficha de producto: tabs y color ---------- */
  $$('.tabs button').forEach((tab) => {
    tab.addEventListener('click', () => {
      $$('.tabs button').forEach((t) => t.classList.remove('is-active'));
      $$('.tab-panel').forEach((p) => p.classList.remove('is-active'));
      tab.classList.add('is-active');
      const panel = document.getElementById('tab-' + tab.dataset.tab);
      if (panel) panel.classList.add('is-active');
    });
  });

  $$('.js-color-thumb').forEach((thumb) => {
    thumb.addEventListener('click', () => {
      $$('.js-color-thumb').forEach((t) => t.classList.remove('is-active'));
      thumb.classList.add('is-active');
      const select = $('#color-select');
      if (select) select.value = thumb.dataset.color;
      const img = $('#product-image');
      if (img) {
        const swatch = thumb.querySelector('.swatch');
        const color = swatch ? getComputedStyle(swatch).backgroundColor : '';
        img.style.filter = 'drop-shadow(0 18px 24px rgba(8,26,46,.18))';
        img.parentElement.style.background = `radial-gradient(circle at 50% 20%, #ffffff, ${color})`;
      }
    });
  });

  /* ---------- calculadora de tarimas (home) ---------- */
  const calcInputs = ['#calc-units', '#calc-box', '#calc-pallet'].map((s) => $(s));
  if (calcInputs.every(Boolean)) {
    const compute = () => {
      const units = Math.max(0, Number(calcInputs[0].value) || 0);
      const perBox = Math.max(1, Number(calcInputs[1].value) || 1);
      const perPallet = Math.max(1, Number(calcInputs[2].value) || 1);
      const boxes = Math.ceil(units / perBox);
      const pallets = Math.ceil(boxes / perPallet);
      $('#calc-boxes').textContent = boxes.toLocaleString('es-MX');
      $('#calc-pallets').textContent = pallets.toLocaleString('es-MX');
      $('#calc-trips').textContent = (pallets ? Math.ceil(pallets / 22) : 0) + ' camión(es)';
    };
    calcInputs.forEach((i) => i.addEventListener('input', compute));
    compute();
  }

  /* ---------- página de cotización ---------- */
  function renderCart() {
    const list = $('#cart-list');
    if (!list) return;
    const items = cart.read();
    $('#cart-empty').style.display = items.length ? 'none' : 'block';
    list.innerHTML = items.map((item, index) => `
      <div class="cart-item">
        <img src="${item.image || '/static/img/logo.svg'}" alt="">
        <div>
          <strong>${item.product_name}</strong>
          <small>${item.model ? 'Modelo ' + item.model : 'Modelo por definir'}${item.color ? ' · ' + item.color : ''}</small>
          ${item.notes ? `<small>Nota: ${item.notes}</small>` : ''}
        </div>
        <div class="qty">
          <input type="number" min="1" value="${item.quantity}" data-index="${index}" class="js-qty" aria-label="Cantidad">
          <button class="link-danger js-remove" data-index="${index}">Quitar</button>
        </div>
      </div>`).join('');

    $$('.js-qty').forEach((input) => input.addEventListener('change', () => {
      const items2 = cart.read();
      items2[Number(input.dataset.index)].quantity = Math.max(1, Number(input.value) || 1);
      cart.write(items2);
    }));
    $$('.js-remove').forEach((btn) => btn.addEventListener('click', () => cart.remove(Number(btn.dataset.index))));
  }
  renderCart();
  document.addEventListener('cart:change', renderCart);

  async function postJSON(url, payload) {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail && data.detail[0] ? data.detail[0].msg : (data.detail || 'Error al enviar'));
    return data;
  }

  const quoteForm = $('#quote-form');
  if (quoteForm) {
    quoteForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const fb = $('#quote-feedback');
      fb.className = 'form-feedback';
      fb.textContent = 'Enviando…';
      const payload = {
        name: $('#q-name').value,
        email: $('#q-email').value,
        company: $('#q-company').value,
        phone: $('#q-phone').value,
        city: $('#q-city').value,
        industry: $('#q-industry').value,
        message: $('#q-message').value,
        source: 'web',
        items: cart.read()
      };
      try {
        const data = await postJSON('/api/cotizaciones', payload);
        fb.className = 'form-feedback is-ok';
        fb.textContent = `¡Listo! Folio ${data.code}. ${data.message}`;
        quoteForm.reset();
        cart.clear();
        toast('Cotización enviada · folio ' + data.code);
      } catch (err) {
        fb.className = 'form-feedback is-error';
        fb.textContent = 'No pudimos enviar la solicitud: ' + err.message;
      }
    });
  }

  const contactForm = $('#contact-form');
  if (contactForm) {
    contactForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const fb = $('#contact-feedback');
      fb.className = 'form-feedback';
      fb.textContent = 'Enviando…';
      try {
        const data = await postJSON('/api/contacto', {
          name: $('#c-name').value,
          email: $('#c-email').value,
          subject: $('#c-subject').value,
          message: $('#c-message').value
        });
        fb.className = 'form-feedback is-ok';
        fb.textContent = data.message;
        contactForm.reset();
      } catch (err) {
        fb.className = 'form-feedback is-error';
        fb.textContent = 'No pudimos enviar tu mensaje: ' + err.message;
      }
    });
  }

  const newsletter = $('#newsletter-form');
  if (newsletter) {
    newsletter.addEventListener('submit', async (event) => {
      event.preventDefault();
      const fb = $('#newsletter-feedback');
      try {
        const data = await postJSON('/api/suscripciones', { email: newsletter.email.value });
        fb.className = 'form-feedback is-ok';
        fb.textContent = data.message;
        newsletter.reset();
      } catch (err) {
        fb.className = 'form-feedback is-error';
        fb.textContent = 'Revisa tu correo e intenta de nuevo.';
      }
    });
  }

  /* ---------- animaciones al hacer scroll ---------- */
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12 });
  $$('.reveal').forEach((el) => observer.observe(el));

  window.remsaCart = cart;
})();
