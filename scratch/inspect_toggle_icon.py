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
    
    # Go to signup to see the inputs
    driver.find_element(By.ID, "go-to-signup").click()
    time.sleep(1)
    
    icons = driver.find_elements(By.CLASS_NAME, "toggle-password-btn")
    print(f"Found {len(icons)} toggle buttons.")
    for idx, icon in enumerate(icons):
        target = icon.get_attribute("data-target")
        visible = icon.is_displayed()
        location = icon.location
        size = icon.size
        style = icon.get_attribute("style")
        color = driver.execute_script("return window.getComputedStyle(arguments[0]).color;", icon)
        z_index = driver.execute_script("return window.getComputedStyle(arguments[0]).zIndex;", icon)
        opacity = driver.execute_script("return window.getComputedStyle(arguments[0]).opacity;", icon)
        display = driver.execute_script("return window.getComputedStyle(arguments[0]).display;", icon)
        
        print(f"Icon {idx}: target={target}")
        print(f"  Visible in DOM: {visible}")
        print(f"  Location: {location}")
        print(f"  Size: {size}")
        print(f"  Computed Display: {display}")
        print(f"  Computed Color: {color}")
        print(f"  Computed Z-index: {z_index}")
        print(f"  Computed Opacity: {opacity}")
        print(f"  Parent outerHTML: {icon.find_element(By.XPATH, '..').get_attribute('outerHTML')[:120]}...")
        
except Exception as main_err:
    print("INSPECTION CRASHED:", main_err)
finally:
    driver.quit()
