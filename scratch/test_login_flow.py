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
    
    # 2. Fill out the login form
    print("Filing login form...")
    driver.find_element(By.ID, "login-email").send_keys("test_requests@example.com")
    driver.find_element(By.ID, "login-password").send_keys("password123")
    
    # Click Sign In via JS click
    login_form = driver.find_element(By.ID, "login-form")
    login_btn = login_form.find_element(By.XPATH, ".//button[@type='submit']")
    print("Clicking Sign In button...")
    driver.execute_script("arguments[0].click();", login_btn)
    time.sleep(4)
    
    # Check if we logged in
    print("After login click:")
    print("Auth screen hidden?", "hidden" in auth_container.get_attribute("class"))
    print("App screen hidden?", "hidden" in app_container.get_attribute("class"))
    
except Exception as main_err:
    print("TEST CRASHED:", main_err)
finally:
    print("Browser console logs:")
    try:
        for entry in driver.get_log('browser'):
            print(entry)
    except Exception as log_err:
        print("Could not retrieve logs:", log_err)
    driver.quit()
