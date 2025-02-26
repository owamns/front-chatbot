document.addEventListener('DOMContentLoaded', () => {
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');

    function addMessage(message, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
        messageDiv.textContent = message;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function addSources(sources) {
        const sourcesDiv = document.createElement('div');
        sourcesDiv.className = 'sources';
        sourcesDiv.innerHTML = '<strong>Fuentes:</strong><br>' +
            sources.map(s => `📄 ${s.archivo} (página ${s.pagina})`).join('<br>');
        chatMessages.appendChild(sourcesDiv);
    }

    async function sendMessage() {
        const message = userInput.value.trim();
        if (!message) return;

        addMessage(message, true);
        userInput.value = '';

        const spinner = document.createElement('div');
        spinner.className = 'spinner';
        spinner.innerHTML = '<div class="loader"></div>';
        chatMessages.appendChild(spinner);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message })
            });

            const data = await response.json();

            spinner.remove();

            if (data.error) {
                addMessage(`Error: ${data.error}`);
                return;
            }

            addMessage(data.respuesta);
            if (data.fuentes && data.fuentes.length > 0) {
                addSources(data.fuentes);
            }
        } catch (error) {
            spinner.remove();
            addMessage('Error de conexión con el servidor');
        }
    }

    sendBtn.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
});
