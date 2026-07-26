import os

file_path = os.path.join("frontend", "app.js")
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = """    signupForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const submitBtn = signupForm.querySelector("button[type='submit']");
        const originalText = submitBtn.innerHTML;
        const email = document.getElementById("signup-email").value.trim();
        const password = document.getElementById("signup-password").value;
        const confirmPassword = document.getElementById("signup-confirm-password").value;"""

replacement = """    signupForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        console.log("Signup submit listener triggered!");
        const submitBtn = signupForm.querySelector("button[type='submit']");
        const originalText = submitBtn.innerHTML;
        const email = document.getElementById("signup-email").value.trim();
        const password = document.getElementById("signup-password").value;
        const confirmPassword = document.getElementById("signup-confirm-password").value;
        console.log("Email:", email);
        console.log("Password len:", password.length);
        console.log("Confirm Password len:", confirmPassword.length);"""

content_norm = content.replace("\r\n", "\n")
target_norm = target.replace("\r\n", "\n")
repl_norm = replacement.replace("\r\n", "\n")

if target_norm in content_norm:
    content_norm = content_norm.replace(target_norm, repl_norm)
    print("app.js patched with submit logs!")
else:
    print("WARNING: Target not found in app.js!")

# Also add log inside try-catch block of register
target_try = """        try {
            const res = await fetchWithAuth(`${API_BASE}/auth/register`, {"""

repl_try = """        console.log("About to call fetchWithAuth for /api/auth/register");
        try {
            const res = await fetchWithAuth(`${API_BASE}/auth/register`, {"""

target_try_norm = target_try.replace("\r\n", "\n")
repl_try_norm = repl_try.replace("\r\n", "\n")

if target_try_norm in content_norm:
    content_norm = content_norm.replace(target_try_norm, repl_try_norm)
    print("app.js patched with try block logs!")
else:
    print("WARNING: try block target not found!")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content_norm)
print("patch finished.")
