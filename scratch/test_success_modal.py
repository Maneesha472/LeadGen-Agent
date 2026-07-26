import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

try:
    driver = webdriver.Chrome(options=chrome_options)
except Exception as e:
    from selenium.webdriver.edge.options import Options as EdgeOptions
    edge_options = EdgeOptions()
    edge_options.add_argument("--headless")
    driver = webdriver.Edge(options=edge_options)

try:
    driver.get("http://localhost:8002")
    time.sleep(2)
    
    # 1. Click Sign Up
    print("Clicking 'Sign Up' link...")
    driver.find_element(By.ID, "go-to-signup").click()
    time.sleep(1)
    
    # Fill out the signup form
    print("Signing up a test user...")
    driver.find_element(By.ID, "signup-email").send_keys("modal_test@example.com")
    driver.find_element(By.ID, "signup-password").send_keys("password123")
    driver.find_element(By.ID, "signup-confirm-password").send_keys("password123")
    
    # Click Create Account via JS click
    signup_form = driver.find_element(By.ID, "signup-form")
    create_btn = signup_form.find_element(By.XPATH, ".//button[@type='submit']")
    driver.execute_script("arguments[0].click();", create_btn)
    time.sleep(3) # Wait for password hashing and database commit
    
    # 2. Verify Success Modal is active
    print("Verifying if success modal is displayed...")
    success_modal = driver.find_element(By.ID, "success-modal")
    modal_class = success_modal.get_attribute("class")
    print("Success Modal Class List:", modal_class)
    print("Is modal active?", "active" in modal_class)
    
    # 3. Click the Proceed to Sign In button
    print("Clicking 'Proceed to Sign In' button...")
    modal_btn = driver.find_element(By.ID, "success-modal-btn")
    driver.execute_script("arguments[0].click();", modal_btn)
    time.sleep(2)
    
    # 4. Verify redirected to Login Form and email pre-populated
    print("Verifying redirection...")
    login_form = driver.find_element(By.ID, "login-form")
    print("Login Form Class List:", login_form.get_attribute("class"))
    print("Is login form visible?", "hidden" not in login_form.get_attribute("class"))
    login_email_val = driver.find_element(By.ID, "login-email").get_attribute("value")
    print("Prefilled Email:", login_email_val)
    
    # 5. Log in
    print("Logging in...")
    driver.find_element(By.ID, "login-password").send_keys("password123")
    login_btn = login_form.find_element(By.XPATH, ".//button[@type='submit']")
    driver.execute_script("arguments[0].click();", login_btn)
    time.sleep(3)
    
    # Verify logged in
    auth_container = driver.find_element(By.ID, "auth-container")
    app_container = driver.find_element(By.CLASS_NAME, "app-container")
    print("Auth screen hidden?", "hidden" in auth_container.get_attribute("class"))
    print("App screen hidden?", "hidden" in app_container.get_attribute("class"))
    
except Exception as main_err:
    print("TEST CRASHED:", main_err)
finally:
    driver.quit()
