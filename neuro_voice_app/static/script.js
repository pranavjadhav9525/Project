document.addEventListener('DOMContentLoaded', () => {
  const voiceBtn = document.getElementById('voiceBtn');
  const output = document.getElementById('output');
  const saveBtn = document.getElementById('saveBtn');
  const status = document.getElementById('status');

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    if (status) status.textContent = 'Speech recognition not supported in this browser.';
    if (voiceBtn) voiceBtn.disabled = true;
    return;
  }

  const recognition = new SpeechRecognition();
  recognition.interimResults = false;
  recognition.lang = 'en-US';

  if (voiceBtn) {
    voiceBtn.addEventListener('click', () => {
      recognition.start();
      if (status) status.textContent = 'Listening...';
    });
  }

  recognition.onresult = (e) => {
    const transcript = e.results[0][0].transcript || '';
    if (output) output.value = transcript;
    if (status) status.textContent = 'Captured. Press Save to store.';
  };

  recognition.onerror = (e) => {
    if (status) status.textContent = 'Error capturing voice: ' + (e.error || 'unknown');
  };

  if (saveBtn) {
    saveBtn.addEventListener('click', () => {
      const text = output.value.trim();
      if (!text) return;
      fetch('/save_query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: text })
      }).then(r => r.json()).then(j => {
        if (j.status === 'ok') {
          status.textContent = 'Saved successfully';
          setTimeout(()=> location.reload(), 600);
        } else {
          status.textContent = 'Save failed';
        }
      }).catch(err => {
        status.textContent = 'Network error';
      });
    });
  }
});
