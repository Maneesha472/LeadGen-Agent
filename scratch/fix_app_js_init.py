import os

file_path = os.path.join("frontend", "app.js")
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = """document.addEventListener("DOMContentLoaded", () => {
    console.log("DOMContentLoaded triggered!");
    initTabs();
    initLeadsManager();
    initAgentRunner();
    console.log("Calling initAuth...");
    initAuth();
    console.log("initAuth execution finished!");
    checkSession();
});"""

replacement = """function startApp() {
    console.log("startApp running...");
    initTabs();
    initLeadsManager();
    initAgentRunner();
    initAuth();
    checkSession();
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", startApp);
} else {
    startApp();
}"""

content_norm = content.replace("\r\n", "\n")
target_norm = target.replace("\r\n", "\n")
repl_norm = replacement.replace("\r\n", "\n")

if target_norm in content_norm:
    content_norm = content_norm.replace(target_norm, repl_norm)
    print("app.js readyState fix applied!")
else:
    print("WARNING: Target DOMContentLoaded block not found in app.js!")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content_norm)
print("patch finished.")
