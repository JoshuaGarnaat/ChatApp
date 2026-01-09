var ws = null;
var currentConversation = null;
var conversations = {}; // {username: [messages]}

const SEND_MESSAGE = "SEND_MESSAGE";
const CREATE_GROUP = "CREATE_GROUP";
const JOIN_GROUP = "JOIN_GROUP";
const SEND_GROUP_MESSAGE = "SEND_GROUP_MESSAGE";

// Helper functions

function isValidUsername(u) {
    return (u.length >= 5 && u.length <= 20 && /^[A-Za-z0-9]*$/.test(u)); // Check length and characters
}

function isValidPassword(p) {
    return (p.length >= 8 && p.length <= 128 && /^[A-Za-z0-9]*$/.test(p)); // Check length and characters
}

function isValidGroupname(u) {
    return (u.length >= 1 && u.length <= 64 && /^[A-Za-z0-9 ]*$/.test(u)); // Check length and characters, but allow spaces
}

// API

async function register() {
    const username = document.getElementById("reg-username").value;
    const password = document.getElementById("reg-password").value;

    if (!isValidUsername(username)) return alert("Username must be between 5 and 20 characters using only letters and numbers");
    if (!isValidPassword(password)) return alert("Password must be between 8 and 128 characters using only letters and numbers");

    try {
        const response = await fetch("/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();

        if (!response.ok) return alert(data.detail ?? data.message);

        alert("Registration successful");
    } catch (e) {
        alert("Error: " + e);
    }
}

async function login() {
    const username = document.getElementById("log-username").value;
    const password = document.getElementById("log-password").value;

    if (!isValidUsername(username)) return alert("Username invalid");
    if (!isValidPassword(password)) return alert("Password invalid");

    try {
        const response = await fetch("/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();

        if (!response.ok) return alert(data.detail ?? data.message);

        localStorage.setItem("token", data.token);

        document.getElementById("current-user").innerText = username;
        document.getElementById("login-container").classList.add("hidden");
        document.getElementById("chat-container").classList.remove("hidden");

        await loadPreviousMessages(data.token);
        connectWebSocket(data.token);

    } catch (e) {
        alert("Error: " + e);
    }
}

function logout() {
    localStorage.removeItem("token");

    if (ws) ws.close();

    document.getElementById("login-container").classList.remove("hidden");
    document.getElementById("chat-container").classList.add("hidden");

    document.getElementById("messages").innerHTML = "";
    document.getElementById("conversation-tabs").innerHTML = "";

    conversations = {};
    currentConversation = null;
}

// WebSocket

function connectWebSocket(token) {
    ws = new WebSocket(
        `${location.origin.replace("http", "ws")}/ws?token=${token}`
    );

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if ("info" in data) return;

        const currentUser = document.getElementById("current-user").innerText;
        const partner =
            data.sender === currentUser ? data.receiver : data.sender;

        storeMessage(partner, data.sender, data.message);
        addConversationTab(partner);

        if (currentConversation === partner) {
            displayMessages(partner);
        }
    };
}

// Messaging

function sendMessage() {
    const receiver = document.getElementById("ws-username").value;
    const message = document.getElementById("ws-message").value;

    if (!isValidUsername(receiver)) return alert("Username invalid");
    if (message === "") return;

    ws.send(
        JSON.stringify({
            req_type: SEND_MESSAGE,
            receiver: receiver,
            message: message
        })
    );

    const currentUser = document.getElementById("current-user").innerText;
    document.getElementById("ws-message").value = "";
}

function storeMessage(conversationUser, sender, message) {
    if (!conversations[conversationUser]) {
        conversations[conversationUser] = [];
    }

    conversations[conversationUser].push({
        sender: sender,
        message: message
    });
}

function displayMessages(username) {
    currentConversation = username;

    const messagesDiv = document.getElementById("messages");
    document.getElementById("ws-username").value = username;
    messagesDiv.innerHTML = "";

    (conversations[username] || []).forEach(msg => {
        messagesDiv.innerHTML +=
            `<div class="msg">
                <strong>${msg.sender}</strong>: ${msg.message}
             </div>`;
    });

    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    updateTabHighlight(username);
}

function addConversationTab(username) {
    const tabsDiv = document.getElementById("conversation-tabs");

    if ([...tabsDiv.children].some(t => t.innerText === username)) return;

    const tab = document.createElement("div");
    tab.className = "tab";
    tab.innerText = username;

    tab.onclick = () => displayMessages(username);

    tabsDiv.appendChild(tab);

    if (!currentConversation) displayMessages(username);
}

function updateTabHighlight(username) {
    [...document.getElementById("conversation-tabs").children].forEach(tab => {
        tab.classList.toggle("active", tab.innerText === username);
    });
}

// Load history

async function loadPreviousMessages(token) {
    try {
        const response = await fetch(`/messages?token=${token}`);
        if (!response.ok) return;

        const data = await response.json();
        const currentUser = document.getElementById("current-user").innerText;

        data.forEach(msg => {
            const partner =
                msg.sender === currentUser ? msg.receiver : msg.sender;

            storeMessage(partner, msg.sender, msg.message);
        });

        Object.keys(conversations).forEach(addConversationTab);

    } catch (e) {
        console.log(e);
    }
}

// Enter to send message
document.addEventListener("DOMContentLoaded", () => {
    const input = document.getElementById("ws-message");

    input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            e.preventDefault();
            sendMessage();
        }
    });
});