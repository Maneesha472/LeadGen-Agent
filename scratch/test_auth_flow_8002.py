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
    
    # 1. We should be on the Sign In screen
    print("Checking initial screen...")
    auth_container = driver.find_element(By.ID, "auth-container")
    app_container = driver.find_element(By.CLASS_NAME, "app-container")
    print("Initial Auth screen hidden?", "hidden" in auth_container.get_attribute("class"))
    print("Initial App screen hidden?", "hidden" in app_container.get_attribute("class"))
    
    # 2. Click Sign Up
    print("Clicking 'Sign Up' link...")
    driver.find_element(By.ID, "go-to-signup").click()
    time.sleep(1)
    
    # Fill out the signup form
    print("Signing up a test user...")
    driver.find_element(By.ID, "signup-email").send_keys("test_flow_complete2@example.com")
    driver.find_element(By.ID, "signup-password").send_keys("password123")
    driver.find_element(By.ID, "signup-confirm-password").send_keys("password123")
    
    # Click Create Account via JS click
    signup_form = driver.find_element(By.ID, "signup-form")
    create_btn = signup_form.find_element(By.XPATH, ".//button[@type='submit']")
    driver.execute_script("arguments[0].click();", create_btn)
    time.sleep(3) # Wait for password hashing and database commit
    
    # 3. Verify we are redirected back to the Sign In form and email is filled
    print("Checking if redirected to login...")
    login_form = driver.find_element(By.ID, "login-form")
    print("Login form hidden?", "hidden" in login_form.get_attribute("class"))
    login_email_val = driver.find_element(By.ID, "login-email").get_attribute("value")
    print("Login email filled:", login_email_val)
    
    # Fill password and click Sign In
    print("Logging in...")
    driver.find_element(By.ID, "login-password").clear()
    driver.find_element(By.ID, "login-password").send_keys("password123")
    login_btn = login_form.find_element(By.XPATH, ".//button[@type='submit']")
    driver.execute_script("arguments[0].click();", login_btn)
    time.sleep(3)
    
    # 4. Verify we are logged in and dashboard is visible
    print("After login: Auth screen hidden?", "hidden" in auth_container.get_attribute("class"))
    print("After login: App screen hidden?", "hidden" in app_container.get_attribute("class"))
    
    # 5. Click Logout
    print("Clicking Log Out button...")
    logout_btn = driver.find_element(By.ID, "logout-btn")
    driver.execute_script("arguments[0].click();", logout_btn)
    time.sleep(2)
    
    # 6. Verify we are back to the Sign In screen
    print("After logout: Auth screen hidden?", "hidden" in auth_container.get_attribute("class"))
    print("After logout: App screen hidden?", "hidden" in app_container.get_attribute("class"))
    
    # 7. Try logging in again
    print("Logging in again...")
    driver.find_element(By.ID, "login-password").clear()
    driver.find_element(By.ID, "login-password").send_keys("password123")
    driver.execute_script("arguments[0].click();", login_btn)
    time.sleep(3)
    print("After re-login: Auth screen hidden?", "hidden" in auth_container.get_attribute("class"))
    print("After re-login: App screen hidden?", "hidden" in app_container.get_attribute("class"))
    
except Exception as main_err:
    print("TEST CRASHED:", main_err)
finally:
    driver.quit()
