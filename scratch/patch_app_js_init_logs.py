import os

file_path = os.path.join("frontend", "app.js")
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = """document.addEventListener("DOMContentLoaded", () => {
    initTabs();
    initLeadsManager();
    initAgentRunner();
    initAuth();
    
    // Check user session
    checkSession();
});"""

replacement = """document.addEventListener("DOMContentLoaded", () => {
    console.log("DOMContentLoaded triggered!");
    initTabs();
    initLeadsManager();
    initAgentRunner();
    console.log("Calling initAuth...");
    initAuth();
    console.log("initAuth execution finished!");
    checkSession();
});"""

content_norm = content.replace("\r\n", "\n")
target_norm = target.replace("\r\n", "\n")
repl_norm = replacement.replace("\r\n", "\n")

if target_norm in content_norm:
    content_norm = content_norm.replace(target_norm, repl_norm)
    print("DOMContentLoaded patched successfully!")
else:
    print("WARNING: DOMContentLoaded target NOT found!")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content_norm)
print("patch finished.")
