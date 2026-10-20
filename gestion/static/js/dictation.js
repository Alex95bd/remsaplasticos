// Dictado con Web Speech API (es-MX). Si el navegador no la soporta se usa el campo de texto.
// El texto reconocido solo se interpreta en el servidor; nada se guarda sin confirmación.
(() => {
  "use strict";
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const box = document.getElementById("speech-box");
  const unsupported = document.getElementById("speech-unsupported");
  const textarea = document.getElementById("id_transcript");
  const source = document.getElementById("id_source");
  if (!Recognition) { unsupported.classList.remove("d-none"); return; }
  box.classList.remove("d-none");
  const button = document.getElementById("mic-btn");
  const status = document.getElementById("mic-status");
  const recognition = new Recognition();
  recognition.lang = "es-MX";
  recognition.interimResults = true;
  recognition.continuous = false;
  let listening = false;

  recognition.onstart = () => { listening = true; button.querySelector("span").textContent = "Detener"; status.textContent = "Escuchando…"; };
  recognition.onend = () => { listening = false; button.querySelector("span").textContent = "Iniciar dictado"; status.textContent = textarea.value ? "Revisa el texto y presiona Interpretar." : ""; };
  recognition.onerror = (event) => {
    status.textContent = event.error === "not-allowed" ? "Permiso de micrófono denegado. Escribe el texto." : `No se pudo reconocer la voz (${event.error}).`;
  };
  recognition.onresult = (event) => {
    let text = "";
    for (const result of event.results) text += result[0].transcript;
    textarea.value = text.trim();
    source.value = "voz";
  };
  textarea.addEventListener("input", () => { source.value = "texto"; });
  button.addEventListener("click", () => (listening ? recognition.stop() : recognition.start()));
})();
