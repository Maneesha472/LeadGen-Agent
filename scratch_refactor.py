import os

with open('backend/scraper.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('import os\nimport re', 'import os\nimport re\nimport logging')

new_log_progress = '''
# ─── Standard Logging Setup ───────────────────────────────────────────────────
def setup_logger(execution_id: int) -> logging.Logger:
    logger = logging.getLogger(f"Execution_{execution_id}")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter('[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        fh = logging.FileHandler(os.path.join(LOGS_DIR, f"run_{execution_id}.log"), encoding="utf-8")
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)
    return logger

def log_progress(execution_id: int, message: str) -> None:
    setup_logger(execution_id).info(message)
'''

old_log_progress = '''def log_progress(execution_id, message):
    log_file = os.path.join(LOGS_DIR, f"run_{execution_id}.log")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_msg = f"[{timestamp}] {message}\\n"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(formatted_msg)
    try:
        print(formatted_msg.strip())
    except UnicodeEncodeError:
        print(formatted_msg.strip().encode('ascii', 'replace').decode('ascii'))'''

content = content.replace(old_log_progress, new_log_progress)

global_session = '''
# ─── Global Request Session ───────────────────────────────────────────────────
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Optional, Dict, Any, List

GLOBAL_SESSION = requests.Session()
_retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
GLOBAL_SESSION.mount("http://", HTTPAdapter(max_retries=_retries))
GLOBAL_SESSION.mount("https://", HTTPAdapter(max_retries=_retries))

def smart_fetch(url: str, execution_id: int = 0) -> str:
'''

content = content.replace('def smart_fetch(url: str, execution_id: int = 0) -> str:', global_session)
content = content.replace('requests.get(url', 'GLOBAL_SESSION.get(url')
content = content.replace('requests.post(\n', 'GLOBAL_SESSION.post(\n')
content = content.replace('except: return', 'except requests.RequestException: return')
content = content.replace('except:\n        return None', 'except Exception:\n        return None')

with open('backend/scraper.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Phase 3 and 6 applied via script')
