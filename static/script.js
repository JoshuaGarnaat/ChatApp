

// Helper functions

function isValidUsername(u) {
    return (u.length >= 5 && u.length <= 20 && /^[A-Za-z0-9]*$/.test(u)); // Check length and characters
}

function isValidPassword(p) {
    return (p.length >= 8 && p.length <= 128 && /^[A-Za-z0-9]*$/.test(p)); // Check length and characters
}


// API

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
}
