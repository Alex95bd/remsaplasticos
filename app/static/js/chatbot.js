/* Widget del asistente virtual "Remi" */
(function () {
  'use strict';

  const panel = document.getElementById('chat-panel');
  const fab = document.getElementById('chat-fab');
  if (!panel || !fab) return;

  const log = document.getElementById('chat-log');
  const form = document.getElementById('chat-form');
  const input = document.getElementById('chat-input');
  const suggestionBox = document.getElementById('chat-suggestions');
  const SESSION_KEY = 'remsa_chat_session';
  let sessionId = localStorage.getItem(SESSION_KEY) || '';
  let greeted = false;

  const format = (text) => text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|[\s(])(\/[a-z0-9\-/]+)/gi, '$1<a href="$2">$2</a>');

  function addMessage(text, who) {
    const el = document.createElement('div');
    el.className = 'msg msg--' + who;
    el.innerHTML = format(text);
    log.appendChild(el);
    log.scrollTop = log.scrollHeight;
    return el;
  }

  function addProducts(products) {
    if (!products || !products.length) return;
    const wrap = document.createElement('div');
    wrap.className = 'chat-products';
    wrap.innerHTML = products.map((p) => `
      <a class="chat-product" href="${p.url}">
        <img src="${p.image || '/static/img/logo.svg'}" alt="">
        <span><strong>${p.name}</strong><small>${p.material} · ${p.capacity}</small></span>
      </a>`).join('');
    log.appendChild(wrap);
    log.scrollTop = log.scrollHeight;
  }

  function setSuggestions(items) {
    suggestionBox.innerHTML = '';
    (items || []).forEach((text) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.textContent = text;
      btn.addEventListener('click', () => send(text));
      suggestionBox.appendChild(btn);
    });
  }

  function typing(on) {
    let el = document.getElementById('typing');
    if (on && !el) {
      el = document.createElement('div');
      el.id = 'typing';
      el.className = 'msg msg--bot typing';
      el.innerHTML = '<span></span><span></span><span></span>';
      log.appendChild(el);
      log.scrollTop = log.scrollHeight;
    } else if (!on && el) {
      el.remove();
    }
  }

  async function send(text) {
    addMessage(text, 'user');
    setSuggestions([]);
    typing(true);
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, session_id: sessionId })
      });
      const data = await res.json();
      typing(false);
      sessionId = data.session_id;
      localStorage.setItem(SESSION_KEY, sessionId);
      addMessage(data.reply, 'bot');
      addProducts(data.products);
      setSuggestions(data.suggestions);
    } catch (err) {
      typing(false);
      addMessage('Tuvimos un problema de conexión. Intenta de nuevo o escríbenos a contacto@remsa.com.mx.', 'bot');
    }
  }

  function open() {
    panel.classList.add('is-open');
    fab.style.display = 'none';
    input.focus();
    if (!greeted) {
      greeted = true;
      addMessage('¡Hola! Soy **Remi**, el asistente virtual de Remsa. Puedo ayudarte a encontrar el envase adecuado, darte especificaciones técnicas o iniciar tu cotización. ¿Qué necesitas?', 'bot');
      setSuggestions(['Ver catálogo de botellas PET', 'Quiero una cotización', '¿Cuál es el pedido mínimo?', '¿Dónde están ubicados?']);
    }
  }

  function close() {
    panel.classList.remove('is-open');
    fab.style.display = 'flex';
  }

  fab.addEventListener('click', open);
  document.getElementById('chat-close').addEventListener('click', close);
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    input.value = '';
    send(text);
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && panel.classList.contains('is-open')) close();
  });
})();
