// Client-side interactions and theme management for Blind Assistant Portal

document.addEventListener("DOMContentLoaded", () => {
    // 1. Theme Configuration
    const themeToggleBtn = document.getElementById("theme-toggle");
    const body = document.body;

    // Load active theme
    const savedTheme = localStorage.getItem("theme");
    if (savedTheme === "light") {
        body.classList.add("light-mode");
        if (themeToggleBtn) themeToggleBtn.innerHTML = "🌙 Dark Mode";
    } else {
        body.classList.remove("light-mode");
        if (themeToggleBtn) themeToggleBtn.innerHTML = "☀️ Light Mode";
    }

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener("click", () => {
            body.classList.toggle("light-mode");
            const isLight = body.classList.contains("light-mode");
            localStorage.setItem("theme", isLight ? "light" : "dark");
            themeToggleBtn.innerHTML = isLight ? "🌙 Dark Mode" : "☀️ Light Mode";
        });
    }

    // 2. Password Visibility Switch
    const togglePasswordButtons = document.querySelectorAll(".password-toggle-btn");
    togglePasswordButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetId = btn.getAttribute("data-target");
            const inputField = document.getElementById(targetId);
            if (inputField) {
                if (inputField.type === "password") {
                    inputField.type = "text";
                    btn.innerHTML = "👁️";
                } else {
                    inputField.type = "password";
                    btn.innerHTML = "🙈";
                }
            }
        });
    });

    // 3. User Registration Client-Side Validations
    const registerForm = document.getElementById("register-form");
    if (registerForm) {
        registerForm.addEventListener("submit", (e) => {
            const password = document.getElementById("password").value;
            const confirmPassword = document.getElementById("confirm_password").value;
            const alertBox = document.getElementById("client-alert");

            if (password !== confirmPassword) {
                e.preventDefault();
                showAlert(alertBox, "Passwords do not match!", "danger");
            } else if (password.length < 6) {
                e.preventDefault();
                showAlert(alertBox, "Password must be at least 6 characters long.", "danger");
            }
        });
    }

    // Helper to display alert banner
    function showAlert(container, message, type) {
        if (!container) return;
        container.style.display = "block";
        container.className = `alert alert-${type}`;
        container.innerHTML = `⚠️ <span>${message}</span>`;
    }

    // 4. Voice Canvas Wave Visualizer Simulator
    const canvas = document.getElementById("audio-wave-canvas");
    if (canvas) {
        const ctx = canvas.getContext("2d");
        let animationId;
        
        // Match canvas layout size
        canvas.width = canvas.parentElement.offsetWidth;
        canvas.height = 150;

        let step = 0;
        function draw() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            // Draw smooth sine-like canvas waves
            ctx.beginPath();
            ctx.lineWidth = 3;
            ctx.strokeStyle = "rgba(0, 206, 201, 0.8)";
            
            for (let i = 0; i < canvas.width; i++) {
                const y = canvas.height / 2 + Math.sin(i * 0.02 + step) * 20 * Math.sin(i * 0.005);
                if (i === 0) {
                    ctx.moveTo(i, y);
                } else {
                    ctx.lineTo(i, y);
                }
            }
            ctx.stroke();

            // Wave 2
            ctx.beginPath();
            ctx.lineWidth = 2;
            ctx.strokeStyle = "rgba(138, 43, 226, 0.5)";
            for (let i = 0; i < canvas.width; i++) {
                const y = canvas.height / 2 + Math.cos(i * 0.015 - step) * 15 * Math.sin(i * 0.008);
                if (i === 0) {
                    ctx.moveTo(i, y);
                } else {
                    ctx.lineTo(i, y);
                }
            }
            ctx.stroke();

            step += 0.05;
            animationId = requestAnimationFrame(draw);
        }
        draw();

        // Stop animation if page navigation starts
        window.addEventListener("unload", () => {
            cancelAnimationFrame(animationId);
        });
    }

    // 5. Simulated Forgot Password popup
    const forgotPasswordLink = document.getElementById("forgot-password-link");
    if (forgotPasswordLink) {
        forgotPasswordLink.addEventListener("click", (e) => {
            e.preventDefault();
            alert("Password recovery has been sent to the registered primary caretaker email associated with this blind assistant portal.");
        });
    }
});
