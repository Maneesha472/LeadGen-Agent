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
    
    # 1. Check initial state of Login Password field
    login_pw = driver.find_element(By.ID, "login-password")
    print("Initial type of login-password:", login_pw.get_attribute("type"))
    
    # 2. Click the eye toggle button
    toggle_btn = driver.find_element(By.XPATH, "//i[@data-target='login-password']")
    print("Clicking password visibility toggle...")
    driver.execute_script("arguments[0].click();", toggle_btn)
    time.sleep(1)
    
    # 3. Check toggled state
    print("Toggled type of login-password:", login_pw.get_attribute("type"))
    print("Eye icon classes:", toggle_btn.get_attribute("class"))
    
    # 4. Click again to hide
    print("Clicking password visibility toggle again...")
    driver.execute_script("arguments[0].click();", toggle_btn)
    time.sleep(1)
    
    print("Final type of login-password:", login_pw.get_attribute("type"))
    print("Final eye icon classes:", toggle_btn.get_attribute("class"))
    
except Exception as main_err:
    print("TEST CRASHED:", main_err)
finally:
    driver.quit()
