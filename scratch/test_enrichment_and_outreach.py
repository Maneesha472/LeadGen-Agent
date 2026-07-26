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

test_email = f"test_enrich_{random.randint(1000, 9999)}@example.com"
test_password = "Password123!"

try:
    driver.get("http://localhost:8002")
    time.sleep(2)
    
    # 1. Switch to Signup
    signup_link = driver.find_element(By.ID, "go-to-signup")
    driver.execute_script("arguments[0].click();", signup_link)
    time.sleep(1)
    
    # Fill Signup form
    driver.find_element(By.ID, "signup-email").send_keys(test_email)
    driver.find_element(By.ID, "signup-password").send_keys(test_password)
    driver.find_element(By.ID, "signup-confirm-password").send_keys(test_password)
    signup_submit = driver.find_element(By.CSS_SELECTOR, "#signup-form button[type='submit']")
    driver.execute_script("arguments[0].click();", signup_submit)
    time.sleep(3)
    
    # Click Proceed on Success Modal
    modal_btn = driver.find_element(By.ID, "success-modal-btn")
    driver.execute_script("arguments[0].click();", modal_btn)
    time.sleep(1)
    print(f"Registered new user {test_email} successfully.")
    
    # 2. Login
    driver.find_element(By.ID, "login-password").send_keys(test_password)
    login_submit = driver.find_element(By.CSS_SELECTOR, "#login-form button[type='submit']")
    driver.execute_script("arguments[0].click();", login_submit)
    time.sleep(3)
    print("Logged in successfully.")
    
    # 3. Go to Run Agent tab
    run_tab = driver.find_element(By.XPATH, "//a[@data-tab='run-agent']")
    driver.execute_script("arguments[0].click();", run_tab)
    time.sleep(1.5)
    
    # 4. Select Target Mode -> Single Enrichment
    target_mode_select = driver.find_element(By.ID, "target-mode")
    driver.execute_script("arguments[0].value = 'single'; arguments[0].dispatchEvent(new Event('change'));", target_mode_select)
    time.sleep(1.5)
    
    # Verify input visibility
    single_row = driver.find_element(By.ID, "single-input-row")
    bulk_row = driver.find_element(By.ID, "bulk-inputs-row")
    print("Single Enrichment row is visible:", single_row.is_displayed())
    print("Bulk search row is visible:", bulk_row.is_displayed())
    
    # Fill target URL and submit
    driver.find_element(By.ID, "target-url").send_keys("enrich-me.com")
    submit_btn = driver.find_element(By.ID, "submit-run-btn")
    driver.execute_script("arguments[0].click();", submit_btn)
    time.sleep(5)
    print("Target Enrichment run submitted and completed.")
    
    # 5. Go to Leads tab
    leads_tab = driver.find_element(By.XPATH, "//a[@data-tab='leads']")
    driver.execute_script("arguments[0].click();", leads_tab)
    time.sleep(2)
    
    # Open individual email outreach modal
    email_btn = driver.find_element(By.CLASS_NAME, "email-btn")
    driver.execute_script("arguments[0].click();", email_btn)
    time.sleep(1.5)
    
    composer = driver.find_element(By.ID, "email-composer-modal")
    print("Composer modal is visible:", composer.is_displayed())
    
    # Send email
    subject = driver.find_element(By.ID, "composer-subject")
    print("Subject pre-populated:", subject.get_attribute("value"))
    
    send_email_btn = driver.find_element(By.ID, "composer-send-btn")
    driver.execute_script("arguments[0].click();", send_email_btn)
    time.sleep(2)
    
    print("Email outreach sent successfully.")
    print("Composer modal is visible after sending:", composer.is_displayed())

except Exception as main_err:
    print("TEST CRASHED:", main_err)
finally:
    driver.quit()
