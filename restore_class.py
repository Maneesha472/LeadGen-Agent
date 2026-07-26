import os

def restore():
    with open('backend/scraper.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # The content currently has `def _process_website(...)` at the top of where the class was.
    header = """
class LeadGenerator:
    def __init__(self, db, execution_id: int):
        self.db = db
        self.execution_id = execution_id
        
        from .database import Execution, User
        self.execution = self.db.query(Execution).filter(Execution.id == self.execution_id).first()
        self.user = self.db.query(User).filter(User.id == self.execution.user_id).first()
        
        import json
        self.settings = {}
        try:
            if self.user and hasattr(self.user, 'settings') and self.user.settings:
                self.settings = json.loads(self.user.settings)
        except Exception:
            pass

    def run(self):
        try:
            self._run_live_scraping()
        except Exception as e:
            log_progress(self.execution_id, f"[ERROR] Scraper crashed: {e}")
            if self.execution:
                self.execution.status = "Failed"
                self.db.commit()

"""
    
    # We replace the standalone `def _process_website` with the class header + indented `_process_website`
    # But wait, my previous replace_file_content left `def _process_website(self, ...)` with 4 spaces indent!
    # So it is already indented for a class.
    # We just need to insert the header before it.
    
    content = content.replace('    def _process_website(self, site: dict, location_hint: str, groq_key: str, category: str, location: str):',
                              header + '    def _process_website(self, site: dict, location_hint: str, groq_key: str, category: str, location: str):')
                              
    with open('backend/scraper.py', 'w', encoding='utf-8') as f:
        f.write(content)
        
if __name__ == "__main__":
    restore()
