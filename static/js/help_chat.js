document.addEventListener('DOMContentLoaded', () => {
    const chatMessages = document.getElementById('chatMessages');
    const chatInput = document.getElementById('chatInput');
    const sendChatButton = document.getElementById('sendChatButton');
    const chatConnectionError = document.getElementById('chatConnectionError');

    // Generar un sessionId único para esta sesión de chat del cliente
    // Podría ser más robusto, pero para este caso es suficiente.
    const sessionId = `chat_session_${Date.now()}_${Math.random().toString(36).substring(2, 15)}`;

    function initializeChat() {
        chatInput.disabled = false;
        sendChatButton.disabled = false;
        chatConnectionError.textContent = '';
        appendMessage('Conectado al asistente. ¡Puedes empezar a chatear!', 'system');
        // Quitar el mensaje inicial estático de help.html ya que el JS lo manejará
        const initialBotMessage = chatMessages.querySelector('.flex.justify-start .bg-indigo-500');
        if (initialBotMessage) {
            initialBotMessage.parentElement.remove();
        }
    }

    function appendMessage(message, sender) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('flex', 'mb-2');

        const contentElement = document.createElement('div');
        contentElement.classList.add('p-3', 'rounded-lg', 'max-w-xs', 'shadow', 'text-sm');

        if (sender === 'user') {
            messageElement.classList.add('justify-end');
            contentElement.classList.add('bg-purple-500', 'text-white');
        } else if (sender === 'bot') {
            messageElement.classList.add('justify-start');
            contentElement.classList.add('bg-indigo-500', 'text-white'); // Estilo original del bot
        } else if (sender === 'system') {
            messageElement.classList.add('justify-center');
            contentElement.classList.add('bg-gray-300', 'text-gray-700', 'italic');
        } else if (sender === 'error') {
            messageElement.classList.add('justify-center');
            contentElement.classList.add('bg-red-200', 'text-red-700', 'font-semibold');
        }

        const p = document.createElement('p');
        p.textContent = message;
        contentElement.appendChild(p);
        messageElement.appendChild(contentElement);
        chatMessages.appendChild(messageElement);
        chatMessages.scrollTop = chatMessages.scrollHeight; // Auto-scroll to last message
    }

    async function sendMessage() {
        const userMessage = chatInput.value.trim();
        if (!userMessage) {
            return;
        }

        appendMessage(userMessage, 'user');
        chatInput.value = '';
        sendChatButton.disabled = true; // Disable button while waiting for response

        try {
            const response = await fetch('/api/chatbot/conversation', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    userMessage: userMessage,
                    sessionId: sessionId, // Enviar el sessionId
                    messageType: 'text' // Opcional, pero puede ser útil
                }),
            });

            sendChatButton.disabled = false; // Re-enable button

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: `Error del servidor: ${response.status}` }));
                console.error('Error from server:', errorData);
                appendMessage(errorData.error || 'Error al obtener respuesta del servidor.', 'error');
                chatConnectionError.textContent = errorData.error || 'Error del servidor.';
                return;
            }

            const data = await response.json();
            console.log('Received response:', data);

            if (data.error) {
                appendMessage(`Error del bot: ${data.error}`, 'error');
            } else if (data.response) {
                appendMessage(data.response, 'bot');
            } else {
                appendMessage('No se recibió una respuesta válida del bot.', 'error');
            }
            chatConnectionError.textContent = ''; // Clear any previous connection errors

        } catch (error) {
            sendChatButton.disabled = false; // Re-enable button on network error
            console.error('Error sending message:', error);
            appendMessage('Error de red al intentar contactar al asistente.', 'error');
            chatConnectionError.textContent = 'Error de red. Verifica tu conexión e intenta de nuevo.';
        }
    }

    sendChatButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            sendMessage();
            event.preventDefault(); // Prevenir el comportamiento por defecto del Enter en un formulario
        }
    });

    // Inicializar el chat
    initializeChat();
});
