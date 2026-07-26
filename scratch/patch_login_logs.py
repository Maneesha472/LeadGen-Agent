import os

file_path = os.path.join("frontend", "app.js")
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

content_norm = content.replace("\r\n", "\n")

target = """    loginForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const submitBtn = loginForm.querySelector("button[type='submit']");"""

replacement = """    loginForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        console.log("Login submit listener triggered!");
        const submitBtn = loginForm.querySelector("button[type='submit']");"""

if target in content_norm:
    content_norm = content_norm.replace(target, replacement)
    print("Login submit handler patched with console log!")
else:
    print("WARNING: Login submit handler target not found!")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content_norm)
print("patch finished.")
