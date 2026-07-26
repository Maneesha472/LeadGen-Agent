import os

file_path = os.path.join("frontend", "app.js")
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

content_norm = content.replace("\r\n", "\n")

# Patch login catch block
target_login = """        } catch (err) {
            showToast("Network error trying to sign in.", "error");"""

repl_login = """        } catch (err) {
            console.error("LOGIN CATCH ERROR:", err, err.stack);
            showToast("Network error trying to sign in.", "error");"""

# Patch signup catch block
target_signup = """        } catch (err) {
            showToast("Network error trying to register.", "error");"""

repl_signup = """        } catch (err) {
            console.error("SIGNUP CATCH ERROR:", err, err.stack);
            showToast("Network error trying to register.", "error");"""

if target_login in content_norm:
    content_norm = content_norm.replace(target_login, repl_login)
    print("Login catch patched!")
else:
    print("WARNING: Login catch target not found!")

if target_signup in content_norm:
    content_norm = content_norm.replace(target_signup, repl_signup)
    print("Signup catch patched!")
else:
    print("WARNING: Signup catch target not found!")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content_norm)
print("patch finished.")
