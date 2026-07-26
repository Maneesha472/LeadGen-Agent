import os

file_path = os.path.join("frontend", "app.js")
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

content_norm = content.replace("\r\n", "\n")

# Remove startApp logs
content_norm = content_norm.replace('    console.log("startApp running...");', '')

# Remove initTabs logs
content_norm = content_norm.replace('    console.log("initTabs finished.");', '')

# Remove initLeadsManager logs
content_norm = content_norm.replace('    console.log("initLeadsManager finished.");', '')

# Remove initAgentRunner logs
content_norm = content_norm.replace('    console.log("initAgentRunner finished.");', '')

# Remove initAuth logs
content_norm = content_norm.replace('    console.log("initAuth finished.");', '')

# Remove login submit listener logs
content_norm = content_norm.replace('        console.log("Login submit listener triggered!");', '')

# Remove signup submit listener logs
content_norm = content_norm.replace('        console.log("Signup submit listener triggered!");', '')
content_norm = content_norm.replace('        console.log("Email:", email);', '')
content_norm = content_norm.replace('        console.log("Password len:", password.length);', '')
content_norm = content_norm.replace('        console.log("Confirm Password len:", confirmPassword.length);', '')
content_norm = content_norm.replace('        console.log("About to call fetchWithAuth for /api/auth/register");', '')

# Remove catch block logs
content_norm = content_norm.replace('            console.error("LOGIN CATCH ERROR:", err, err.stack);', '')
content_norm = content_norm.replace('            console.error("SIGNUP CATCH ERROR:", err, err.stack);', '')

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content_norm)
print("app.js logs cleaned up successfully!")
