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
    # Inject log capturing script BEFORE the page loads
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': """
            window.capturedLogs = [];
            window.console.log = function(...args) {
                window.capturedLogs.push(args.join(' '));
            };
            window.capturedErrors = [];
            window.console.error = function(...args) {
                window.capturedErrors.push(args.join(' '));
            };
            window.onerror = function(msg, url, line, col, err) {
                window.capturedErrors.push(msg + " at " + line + ":" + col);
                return false;
            };
        """
    })

    driver.get("http://localhost:8002")
    time.sleep(2)
    
    # Fill out the login form
    driver.find_element(By.ID, "login-email").send_keys("test_requests@example.com")
    driver.find_element(By.ID, "login-password").send_keys("password123")
    
    # Dispatch submit event
    print("Dispatching submit event...")
    driver.execute_script("""
        var form = document.getElementById('login-form');
        var event = new Event('submit', { cancelable: true, bubbles: true });
        form.dispatchEvent(event);
    """)
    
    time.sleep(2)
    
    # Retrieve and print logs
    logs = driver.execute_script("return window.capturedLogs;")
    errors = driver.execute_script("return window.capturedErrors;")
    print("CAPTURED CONSOLE LOGS:")
    for l in logs:
        print("  LOG:", l)
    print("CAPTURED CONSOLE ERRORS:")
    for e in errors:
        print("  ERROR:", e)
        
finally:
    driver.quit()
