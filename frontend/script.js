
const API_BASE = window.DMS_API_BASE;

// Switch to Login form
function showLogin() {
    document.getElementById("loginForm").style.display = "block";
    document.getElementById("registerForm").style.display = "none";

    document.getElementById("loginTab").classList.add("active");
    document.getElementById("registerTab").classList.remove("active");

    clearMessage();
}

// Switch to Registration form
function showRegister() {
    document.getElementById("loginForm").style.display = "none";
    document.getElementById("registerForm").style.display = "block";

    document.getElementById("registerTab").classList.add("active");
    document.getElementById("loginTab").classList.remove("active");

    clearMessage();
}

// Display messages
function showMessage(text, type = "error") {
    const message = document.getElementById("message");
    message.textContent = text;
    message.className = type;
}

function clearMessage() {
    const message = document.getElementById("message");
    message.textContent = "";
    message.className = "";
}

// Register a new user
document.getElementById("registerForm").addEventListener("submit", async (event) => {
    event.preventDefault();

    const username = document.getElementById("registerUsername").value.trim();
    const email = document.getElementById("registerEmail").value.trim();
    const password = document.getElementById("registerPassword").value;
    const division = document.getElementById("registerDivision").value;

    try {
        showMessage("Registering...", "success");

        const response = await fetch(`${API_BASE}/auth/register`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                username,
                email,
                password,
                division
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.error || data.message || "Registration failed"
            );
        }

        showLogin();
        document.getElementById("loginEmail").value = email;
        document.getElementById("registerForm").reset();

        showMessage(
            "Registration successful! Please log in.",
            "success"
        );

    } catch (error) {
        showMessage(error.message);
    }
});

// Login an existing user
document.getElementById("loginForm").addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = document.getElementById("loginEmail").value.trim();
    const password = document.getElementById("loginPassword").value;

    try {
        showMessage("Logging in...", "success");

        const response = await fetch(`${API_BASE}/auth/login`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                email,
                password
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.error || data.message || "Login failed"
            );
        }

        if (!data.access_token) {
            throw new Error(
                "Login response did not contain an access token"
            );
        }

        // Store JWT token for the current browser session
        sessionStorage.setItem(
            "access_token",
            data.access_token
        );

        showMessage("Login successful!", "success");

        // Redirect to Document Management Dashboard
        window.location.href = "dashboard.html";

    } catch (error) {
        showMessage(error.message);
    }
});
