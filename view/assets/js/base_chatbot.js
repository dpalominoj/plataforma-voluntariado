document.addEventListener('DOMContentLoaded', () => {
  const voiceChatTriggerButton = document.getElementById('voiceChatTrigger');
  // Ensure this button exists, otherwise the script might error if base_chatbot.js is loaded on pages
  // where the chatbot menu (and thus voiceChatTriggerButton) is not present.
  // However, the chatbot icon and menu are intended to be on all pages via base.html.
  if (!voiceChatTriggerButton) {
      // console.log("Voice chat trigger button not found on this page.");
      // If it's absolutely critical for it to be on every page, this check might be less important.
      // For now, let's assume it will be there as it's part of base.html.
      // If not, the script will fail at getElementById unless checked.
      // A more robust check:
      // if (!voiceChatTriggerButton) return; // Exit if no button
  }

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const speechSynthesis = window.speechSynthesis;

  let recognition;
  let isRecognizing = false;

  if (SpeechRecognition && speechSynthesis) {
    if (!voiceChatTriggerButton) {
        console.warn("Voice chat trigger button ('voiceChatTrigger') not found. Voice chat cannot be initialized.");
        return; // Exit if button not found
    }

    recognition = new SpeechRecognition();
    recognition.lang = 'es-ES';
    recognition.interimResults = false;
    recognition.continuous = false; // Stop after first utterance

    const speak = (text) => {
      if (speechSynthesis.speaking) {
        console.warn('SpeechSynthesis is already speaking. Cancelling previous utterance.');
        speechSynthesis.cancel();
      }
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'es-ES';
      speechSynthesis.speak(utterance);
    };

    voiceChatTriggerButton.addEventListener('click', () => {
      if (isRecognizing) {
        recognition.stop();
        return;
      }
      try {
        recognition.start();
      } catch (e) {
        console.error("Error starting recognition (possibly already started):", e);
        if (isRecognizing) {
          recognition.stop();
        }
      }
    });

    recognition.onstart = () => {
      isRecognizing = true;
      console.log('Voice recognition started. Speak into the microphone.');
      voiceChatTriggerButton.textContent = 'Escuchando...';
      voiceChatTriggerButton.disabled = true;
      document.body.classList.add('voice-recognizing-for-base');
    };

    recognition.onresult = (event) => {
      const transcript = event.results[event.results.length - 1][0].transcript.trim();
      console.log('Recognized text:', transcript);
      speak(`He entendido: ${transcript}`);
    };

    recognition.onerror = (event) => {
      console.error('Speech recognition error:', event.error);
      let errorMessage = 'Hubo un error con el reconocimiento de voz.';
      if (event.error === 'no-speech') {
        errorMessage = 'No se detectó voz. Inténtalo de nuevo.';
      } else if (event.error === 'audio-capture') {
        errorMessage = 'Error de captura de audio. Asegúrate de que el micrófono funciona.';
      } else if (event.error === 'not-allowed') {
        errorMessage = 'Permiso para usar el micrófono denegado. Habilítalo en la configuración de tu navegador.';
      }
      speak(errorMessage);
    };

    recognition.onend = () => {
      isRecognizing = false;
      console.log('Voice recognition ended.');
      voiceChatTriggerButton.textContent = 'Chatbot por voz';
      voiceChatTriggerButton.disabled = false;
      document.body.classList.remove('voice-recognizing-for-base');
    };

  } else {
    console.warn('Speech Recognition or Synthesis not supported in this browser.');
    if (voiceChatTriggerButton) {
      voiceChatTriggerButton.textContent = 'Voz no soportada';
      voiceChatTriggerButton.disabled = true;
      voiceChatTriggerButton.title = 'Tu navegador no soporta las APIs de voz necesarias.';
      voiceChatTriggerButton.classList.add('opacity-50', 'cursor-not-allowed');
    }
  }
});
