var ws = null;

const SEND_MESSAGE = "SEND_MESSAGE";
const CREATE_GROUP = "CREATE_GROUP";
const JOIN_GROUP = "JOIN_GROUP";

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

// Handle registration
async function register() {
    const username = document.getElementById("reg-username").value;
    const password = document.getElementById("reg-password").value;

    // Client-side validation
    if (!isValidUsername(username)) {
        return alert("Username invalid");
    }
    if (!isValidPassword(password)) {
        return alert("Password invalid");
    }

    try {
        // Fetch
        const response = await fetch("/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        if (!response.ok) {
            return alert("Error: " + data.detail ?? data.message);
        }

        alert("Registration successful");
    }
    catch (e) {
        alert("Error: " + e);
    }
}

// Handle login
async function login() {
    const username = document.getElementById("log-username").value;
    const password = document.getElementById("log-password").value;

    // Client-side validation
    if (!isValidUsername(username)) {
        return alert("Username invalid");
    }
    if (!isValidPassword(password)) {
        return alert("Password invalid");
    }

    try {
        // Fetch
        const response = await fetch("/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        // Store token for WebSocket authentication
        localStorage.setItem("token", data.token);
        var expire_date = new Date(data.expires_at * 1000);
        alert("Login successful. Token expires at " + expire_date);
    }
    catch (e) {
        alert("Error: " + e);
    }
    var token = localStorage.getItem("token");
    if (!token) {
        alert("Token does not exist");
    }
    connectWebSocket(token);
}

// Connect and setup websocket
function connectWebSocket(token) {
    // Create a websocket
    ws = new WebSocket(`${location.origin.replace("http", "ws")}/ws?token=${token}`);
    // Run on message received
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log(data);
    };
}

// Send message
async function sendMessage() {
    const username = document.getElementById("ws-username").value;
    const message = document.getElementById("ws-message").value;

    // Client-side validation
    if (!isValidUsername(username)) {
        return alert("Username invalid");
    }

    // Send JSON containing the request type, receiver, username and message
    ws.send(JSON.stringify({"req_type": SEND_MESSAGE, "receiver": username, "message": message}));
}

async function createGroup() {
    const groupname = document.getElementById("cr-groupname").value;
    
    // Client-side validation
    if (!isValidGroupname(groupname)) {
        return alert("Groupname invalid");
    }

    // Send JSON containing the request type and groupname
    ws.send(JSON.stringify({"req_type": CREATE_GROUP ,"groupname": groupname}));
}

// Check for token on start
// var token = localStorage.getItem("token");
// if (token) {
//     // Start websocket if token available
//     connectWebSocket(token);
// }
