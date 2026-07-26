import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select

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

test_email = f"test_camp_{random.randint(1000, 9999)}@example.com"
test_password = "Password123!"

try:
    driver.get("http://localhost:8002")
    time.sleep(2)
    
    # 1. Register a user
    signup_link = driver.find_element(By.ID, "go-to-signup")
    driver.execute_script("arguments[0].click();", signup_link)
    time.sleep(1)
    
    driver.find_element(By.ID, "signup-email").send_keys(test_email)
    driver.find_element(By.ID, "signup-password").send_keys(test_password)
    driver.find_element(By.ID, "signup-confirm-password").send_keys(test_password)
    signup_submit = driver.find_element(By.CSS_SELECTOR, "#signup-form button[type='submit']")
    driver.execute_script("arguments[0].click();", signup_submit)
    time.sleep(3)
    
    # Dismiss Success Modal
    modal_btn = driver.find_element(By.ID, "success-modal-btn")
    driver.execute_script("arguments[0].click();", modal_btn)
    time.sleep(1)
    
    # 2. Log in
    driver.find_element(By.ID, "login-password").send_keys(test_password)
    login_submit = driver.find_element(By.CSS_SELECTOR, "#login-form button[type='submit']")
    driver.execute_script("arguments[0].click();", login_submit)
    time.sleep(3)
    print("User authenticated successfully.")
    
    # 3. Go to Run Agent tab
    run_tab = driver.find_element(By.XPATH, "//a[@data-tab='run-agent']")
    driver.execute_script("arguments[0].click();", run_tab)
    time.sleep(1.5)
    
    # Select Single Target Mode
    target_mode_select = driver.find_element(By.ID, "target-mode")
    driver.execute_script("arguments[0].value = 'single'; arguments[0].dispatchEvent(new Event('change'));", target_mode_select)
    time.sleep(1.5)
    
    # Fill target website and launch (scrapes only)
    driver.find_element(By.ID, "target-url").send_keys("leadtune.com")
    submit_run_btn = driver.find_element(By.ID, "submit-run-btn")
    driver.execute_script("arguments[0].click();", submit_run_btn)
    time.sleep(6) # Let scraping complete
    print("Scraper run completed. Lead generated.")
    
    # 4. Go to Outreach Campaigns tab
    outreach_tab = driver.find_element(By.XPATH, "//a[@data-tab='campaigns']")
    driver.execute_script("arguments[0].click();", outreach_tab)
    time.sleep(2)
    
    # Check campaign lead source dropdown
    campaign_source = driver.find_element(By.ID, "campaign-source")
    options = campaign_source.find_elements(By.TAG_NAME, "option")
    print("Campaign source options found:")
    for opt in options:
        print(f" - Value: {opt.get_attribute('value')} | Text: {opt.text}")
        
    # Select the completed run (second option in select dropdown)
    driver.execute_script("arguments[0].selectedIndex = 2; arguments[0].dispatchEvent(new Event('change'));", campaign_source)
    time.sleep(1)
    
    # Fill in campaign template and submit
    driver.find_element(By.ID, "campaign-subject").send_keys("Partnership Inquiry for {company_name}")
    driver.find_element(By.ID, "campaign-body").send_keys("Hi {contact_name},\n\nHope you are doing well.")
    
    submit_campaign_btn = driver.find_element(By.ID, "submit-campaign-btn")
    driver.execute_script("arguments[0].click();", submit_campaign_btn)
    time.sleep(5) # Let outreach campaign run
    print("Outreach Campaign finished.")
    
    # Verify campaign execution stats
    sent_count = driver.find_element(By.ID, "campaign-stat-sent").text
    failed_count = driver.find_element(By.ID, "campaign-stat-failed").text
    print(f"Campaign Stats: Sent = {sent_count} | Failed = {failed_count}")
    
    # Go to Leads Manager tab
    leads_tab = driver.find_element(By.XPATH, "//a[@data-tab='leads']")
    driver.execute_script("arguments[0].click();", leads_tab)
    time.sleep(2)
    
    # Verify leads state updated
    badges = driver.find_elements(By.CSS_SELECTOR, "#leads-table tbody .badge")
    for b in badges:
        print(f"Lead status badge text in directory: {b.text}")

except Exception as main_err:
    print("TEST CRASHED:", main_err)
finally:
    driver.quit()
