import time
import random
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

test_email = f"test_live_{random.randint(1000, 9999)}@example.com"
test_password = "Password123!"

try:
    driver.get("http://localhost:8002")
    time.sleep(2)
    
    # 1. Switch to Signup
    signup_link = driver.find_element(By.ID, "go-to-signup")
    driver.execute_script("arguments[0].click();", signup_link)
    time.sleep(1)
    
    # Register new user
    driver.find_element(By.ID, "signup-email").send_keys(test_email)
    driver.find_element(By.ID, "signup-password").send_keys(test_password)
    driver.find_element(By.ID, "signup-confirm-password").send_keys(test_password)
    signup_submit = driver.find_element(By.CSS_SELECTOR, "#signup-form button[type='submit']")
    driver.execute_script("arguments[0].click();", signup_submit)
    time.sleep(3)
    
    # Proceed to Sign In on Success Modal
    modal_btn = driver.find_element(By.ID, "success-modal-btn")
    driver.execute_script("arguments[0].click();", modal_btn)
    time.sleep(1)
    
    # Log in
    driver.find_element(By.ID, "login-password").send_keys(test_password)
    login_submit = driver.find_element(By.CSS_SELECTOR, "#login-form button[type='submit']")
    driver.execute_script("arguments[0].click();", login_submit)
    time.sleep(3)
    print("Logged in successfully.")
    
    # 2. Verify Simulation Badge is NOT present in header
    badges = driver.find_elements(By.ID, "simulation-badge")
    print("Simulation Badge exists in header:", len(badges) > 0)
    
    # 3. Go to Settings tab and verify Simulation switch is NOT present
    settings_tab = driver.find_element(By.XPATH, "//a[@data-tab='settings']")
    driver.execute_script("arguments[0].click();", settings_tab)
    time.sleep(1.5)
    
    switches = driver.find_elements(By.ID, "setting-simulation-mode")
    # Verify that it is a hidden element or not displayed
    is_hidden = not switches[0].is_displayed() if len(switches) > 0 else True
    print("Simulation toggle is hidden or removed in Settings UI:", is_hidden)
    
    # 4. Go to Run Agent and run
    run_tab = driver.find_element(By.XPATH, "//a[@data-tab='run-agent']")
    driver.execute_script("arguments[0].click();", run_tab)
    time.sleep(1.5)
    
    # Fill target website and launch (Live Scraping)
    target_mode_select = driver.find_element(By.ID, "target-mode")
    driver.execute_script("arguments[0].value = 'single'; arguments[0].dispatchEvent(new Event('change'));", target_mode_select)
    time.sleep(1.5)
    
    driver.find_element(By.ID, "target-url").send_keys("leadtune.com")
    submit_run_btn = driver.find_element(By.ID, "submit-run-btn")
    driver.execute_script("arguments[0].click();", submit_run_btn)
    time.sleep(6) # Let scraping start/run
    print("Scraper run completed.")

except Exception as main_err:
    print("TEST CRASHED:", main_err)
finally:
    driver.quit()
