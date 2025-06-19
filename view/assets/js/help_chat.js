document.addEventListener('DOMContentLoaded', function() {
    const chatMessagesContainer = document.getElementById('chatMessages');
    const chatInput = document.getElementById('chatInput');
    const sendChatButton = document.getElementById('sendChatButton');
    const chatConnectionErrorDiv = document.getElementById('chatConnectionError');

    // Ensure all required DOM elements are present before proceeding
    if (!chatMessagesContainer || !chatInput || !sendChatButton || !chatConnectionErrorDiv) {
        console.error('Required chat DOM elements not found. Chat functionality cannot be initialized.');
        return;
    }

    let socket;
    let botIsTyping = false;
    let initialConnectionTimeout;

    function initializeSocket() {
        if (chatConnectionErrorDiv) {
            chatConnectionErrorDiv.textContent = 'Iniciando conexi&oacute;n con el chat...';
        }

        initialConnectionTimeout = setTimeout(() => {
            if (chatConnectionErrorDiv && (!socket || !socket.connected)) {
                chatConnectionErrorDiv.textContent = 'La conexi&oacute;n est&aacute; tardando. Verifique el servidor o intente recargar.';
            }
        }, 7000);

        socket = io(window.location.origin, {
            reconnectionAttempts: 5,
            reconnectionDelay: 2000,
            timeout: 10000
        });

        socket.on('connect', () => {
            clearTimeout(initialConnectionTimeout);
            console.log('Socket.IO connected:', socket.id);
            chatInput.disabled = false;
            sendChatButton.disabled = false;
            if (chatConnectionErrorDiv) chatConnectionErrorDiv.textContent = '';
        });

        socket.on('disconnect', (reason) => {
            clearTimeout(initialConnectionTimeout);
            console.log('Socket.IO disconnected:', reason);
            chatInput.disabled = true;
            sendChatButton.disabled = true;
            setBotTypingIndicator(false);
            if (chatConnectionErrorDiv && chatConnectionErrorDiv.textContent !== 'La conexi&oacute;n est&aacute; tardando. Verifique el servidor o intente recargar.') {
                if (reason === 'io server disconnect') {
                    chatConnectionErrorDiv.textContent = 'Desconectado por el servidor. Intenta recargar.';
                } else {
                     if (!socket.active) {
                        chatConnectionErrorDiv.textContent = 'Desconectado. Intenta recargar la p&aacute;gina.';
                     }
                }
            }
        });

        socket.on('connect_error', (error) => {
            clearTimeout(initialConnectionTimeout);
            console.error('Socket.IO connection error:', error);
            chatInput.disabled = true;
            sendChatButton.disabled = true;
            setBotTypingIndicator(false);
            if (chatConnectionErrorDiv) chatConnectionErrorDiv.textContent = 'Error de conexi&oacute;n. Verifica tu red e intenta recargar.';
        });

        socket.on('reconnect_attempt', (attemptNumber) => {
            clearTimeout(initialConnectionTimeout);
            console.log(`Socket.IO reconnect attempt ${attemptNumber}`);
            if (chatConnectionErrorDiv) chatConnectionErrorDiv.textContent = `Intentando reconectar (${attemptNumber})...`;
        });

        socket.on('reconnect_failed', () => {
            // Note: initialConnectionTimeout might have already fired and set a message.
            // This handler is for when explicit reconnection attempts by socket.io client fail.
            console.error('Socket.IO reconnection failed');
            if (chatConnectionErrorDiv) chatConnectionErrorDiv.textContent = 'No se pudo reconectar. Por favor, recarga la p&aacute;gina.';
        });

        socket.on('chat_response', (data) => {
            setBotTypingIndicator(false);
            if (data && typeof data.response === 'string') {
                addMessageToChat(data.response, 'bot');
                if (data.requires_auth) {
                    addMessageToChat("Por favor, inicia sesi&oacute;n para obtener respuestas m&aacute;s personalizadas.", 'bot-info');
                }
            } else if (data && typeof data.error === 'string') {
                 addMessageToChat(`Error: ${data.error}`, 'bot-error');
            } else {
                addMessageToChat("Respuesta inesperada del servidor.", 'bot-error');
                console.error("Unexpected chat_response data:", data);
            }
        });

        socket.on('chat_error', (data) => {
            setBotTypingIndicator(false);
            if (data && typeof data.message === 'string') {
                addMessageToChat(data.message, 'bot-error');
            } else {
                addMessageToChat("Ocurri&oacute; un error desconocido con el chat.", 'bot-error');
                console.error("Unknown chat_error:", data);
            }
        });
    }

    function addMessageToChat(message, senderType) {
        const messageWrapper = document.createElement('div');
        messageWrapper.classList.add('flex', 'mb-3', 'clear-both');

        const messageContent = document.createElement('div');
        messageContent.classList.add('p-3', 'rounded-lg', 'max-w-md', 'shadow-md', 'text-sm', 'break-words');

        switch (senderType) {
            case 'user':
                messageWrapper.classList.add('justify-end');
                messageContent.classList.add('bg-blue-500', 'text-white', 'ml-auto');
                break;
            case 'bot-error':
                messageWrapper.classList.add('justify-start');
                messageContent.classList.add('bg-red-600', 'text-white', 'mr-auto', 'max-w-lg');
                messageContent.classList.remove('max-w-md');
                break;
            case 'bot-info':
                messageWrapper.classList.add('justify-start');
                messageContent.classList.add('bg-yellow-400', 'text-gray-800', 'mr-auto', 'max-w-lg');
                messageContent.classList.remove('max-w-md');
                break;
            case 'system':
                messageWrapper.classList.add('justify-center', 'my-2');
                messageContent.classList.add('bg-gray-300', 'text-gray-700', 'mx-auto', 'text-xs', 'px-2', 'py-1');
                break;
            default: // 'bot'
                messageWrapper.classList.add('justify-start');
                messageContent.classList.add('bg-indigo-500', 'text-white', 'mr-auto', 'max-w-lg');
                messageContent.classList.remove('max-w-md');
        }

        const p = document.createElement('p');
        p.style.whiteSpace = 'pre-wrap';
        p.textContent = message;
        messageContent.appendChild(p);

        messageWrapper.appendChild(messageContent);
        chatMessagesContainer.appendChild(messageWrapper);
        chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
    }

    function setBotTypingIndicator(isTyping) {
        botIsTyping = isTyping;

        const connected = socket && socket.connected;
        chatInput.disabled = isTyping || !connected;
        sendChatButton.disabled = isTyping || !connected;

        const typingIndicatorId = 'botTypingIndicator';
        let typingIndicator = document.getElementById(typingIndicatorId);

        if (isTyping) {
            if (!typingIndicator) {
                typingIndicator = document.createElement('div');
                typingIndicator.id = typingIndicatorId;
                typingIndicator.classList.add('flex', 'justify-start', 'mb-3');
                const typingContent = document.createElement('div');
                typingContent.classList.add('bg-gray-200', 'text-gray-600', 'p-3', 'rounded-lg', 'max-w-xs', 'shadow-md', 'text-sm', 'italic');
                typingContent.textContent = 'El asistente est&aacute; escribiendo...';
                typingIndicator.appendChild(typingContent);
                chatMessagesContainer.appendChild(typingIndicator);
                chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
            }
        } else {
            if (typingIndicator) {
                typingIndicator.remove();
            }
        }
    }

    function sendMessage() {
        const messageText = chatInput.value.trim();
        if (!socket || !socket.connected) {
            if (chatConnectionErrorDiv) chatConnectionErrorDiv.textContent = "No est&aacute;s conectado. Intentando reconectar...";
            if (socket && typeof socket.connect === 'function') {
                 // socket.connect(); // Avoid repeated manual connect calls if library handles it.
            } else if (!socket) {
                // initializeSocket(); // Avoid re-initializing if it's already in progress or failed.
            }
            return;
        }
        if (botIsTyping) return;

        if (messageText) {
            addMessageToChat(messageText, 'user');
            socket.emit('chat_message', { query: messageText });
            chatInput.value = '';
            setBotTypingIndicator(true);
        }
    }

    sendChatButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', function(event) {
        if (event.key === 'Enter') {
            event.preventDefault();
            sendMessage();
        }
    });

    initializeSocket();
});
