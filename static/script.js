let ws = new WebSocket("ws://localhost:8000/ws/chat");

ws.onmessage = (event) => {
    let messages = document.getElementById("messages");
    let message = document.createElement("div");
    message.innerText = event.data;
    messages.appendChild(message);
    messages.scrollTop = messages.scrollHeight;
};

function sendMessage() {
    let username = document.getElementById("username").value.trim();
    let messageInput = document.getElementById("messageInput");
    let text = messageInput.value.trim();
    console.log(username, text);

    if (!username || !text) return;

    ws.send(username + ": " + text);
    messageInput.value = "";
}
