import os

file_path = os.path.join("frontend", "app.js")
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Normalize line endings
content_norm = content.replace("\r\n", "\n")

# Inject log at end of initTabs
content_norm = content_norm.replace(
    "navItems.forEach(item => {\n        item.addEventListener(\"click\", (e) => {\n            e.preventDefault();\n            const targetTab = item.getAttribute(\"data-tab\");\n            switchTab(targetTab);\n        });\n    });\n}",
    "navItems.forEach(item => {\n        item.addEventListener(\"click\", (e) => {\n            e.preventDefault();\n            const targetTab = item.getAttribute(\"data-tab\");\n            switchTab(targetTab);\n        });\n    });\n    console.log(\"initTabs finished.\");\n}"
)

# Inject log at end of initLeadsManager
content_norm = content_norm.replace(
    "closeModalBtn.addEventListener(\"click\", () => leadModal.classList.remove(\"active\"));\n    leadModal.addEventListener(\"click\", (e) => {\n        if (e.target === leadModal) {\n            leadModal.classList.remove(\"active\");\n        }\n    });\n}",
    "closeModalBtn.addEventListener(\"click\", () => leadModal.classList.remove(\"active\"));\n    leadModal.addEventListener(\"click\", (e) => {\n        if (e.target === leadModal) {\n            leadModal.classList.remove(\"active\");\n        }\n    });\n    console.log(\"initLeadsManager finished.\");\n}"
)

# Inject log at end of initAgentRunner
content_norm = content_norm.replace(
    "clearConsoleBtn.addEventListener(\"click\", () => {\n        terminalLogs.innerHTML = '<div class=\"terminal-line placeholder-line\">&gt; Ready for instructions.</div>';\n    });\n}",
    "clearConsoleBtn.addEventListener(\"click\", () => {\n        terminalLogs.innerHTML = '<div class=\"terminal-line placeholder-line\">&gt; Ready for instructions.</div>';\n    });\n    console.log(\"initAgentRunner finished.\");\n}"
)

# Inject log at end of initAuth
content_norm = content_norm.replace(
    "logoutBtn.addEventListener(\"click\", () => {\n        localStorage.removeItem(\"token\");\n        showAuthScreen();\n        showToast(\"Logged out successfully.\", \"info\");\n    });\n}",
    "logoutBtn.addEventListener(\"click\", () => {\n        localStorage.removeItem(\"token\");\n        showAuthScreen();\n        showToast(\"Logged out successfully.\", \"info\");\n    });\n    console.log(\"initAuth finished.\");\n}"
)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content_norm)
print("Startup checks injected!")
