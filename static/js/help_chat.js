document.addEventListener('DOMContentLoaded', () => {
    const chatMessages = document.getElementById('chatMessages');
    const chatInput = document.getElementById('chatInput');
    const sendChatButton = document.getElementById('sendChatButton');
    const chatConnectionError = document.getElementById('chatConnectionError');

    let socket;

    function connectSocket() {
        // Asegúrate de que la URL coincida con tu configuración de SocketIO en el servidor
        // Si Flask está sirviendo en el mismo host y puerto, '/' es usualmente suficiente.
        // Si usas un namespace, ajústalo aquí, ej: io('/chat')
        socket = io(window.location.origin);

        socket.on('connect', () => {
            console.log('Connected to chat server.');
            chatInput.disabled = false;
            sendChatButton.disabled = false;
            chatConnectionError.textContent = '';
            appendMessage('Conectado al asistente. ¡Puedes empezar a chatear!', 'system');
        });

        socket.on('disconnect', () => {
            console.log('Disconnected from chat server.');
            chatInput.disabled = true;
            sendChatButton.disabled = true;
            chatConnectionError.textContent = 'Desconectado del servidor de chat. Intentando reconectar...';
            // Podrías intentar reconectar aquí si es necesario, o simplemente informar al usuario.
        });

        socket.on('connect_error', (error) => {
            console.error('Connection Error:', error);
            chatInput.disabled = true;
            sendChatButton.disabled = true;
            chatConnectionError.textContent = 'Error al conectar con el servidor de chat. Verifica la consola para más detalles.';
            appendMessage(`Error de conexión: ${error.message}`, 'error');
        });

        socket.on('chat_response', (data) => {
            console.log('Received response:', data);
            if (data.error) {
                appendMessage(`Error del bot: ${data.error}`, 'error');
            } else {
                appendMessage(data.response, 'bot');
            }
        });
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

    function sendMessage() {
        const message = chatInput.value.trim();
        if (message && socket && socket.connected) {
            appendMessage(message, 'user');
            socket.emit('chat_message', { query: message });
            chatInput.value = '';
        } else if (!socket || !socket.connected) {
            appendMessage('No estás conectado al servidor de chat.', 'error');
        }
    }

    sendChatButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            sendMessage();
        }
    });

    // Inicializar la conexión
    // Quitar el mensaje inicial estático de help.html ya que el JS lo manejará
    const initialBotMessage = chatMessages.querySelector('.flex.justify-start .bg-indigo-500');
    if (initialBotMessage) {
        initialBotMessage.parentElement.remove();
    }

    connectSocket();
});
