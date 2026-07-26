import re

def cleanup():
    with open("backend/scraper.py", "r", encoding="utf-8") as f:
        content = f.read()

    # The first valid end of _run_live_scraping is:
    #             log_progress(self.execution_id, f"Valid Leads: {contacts_added}/{target_leads}\n------------------------------------------------")
    
    # After that, we should have:
    #         self.execution.status = "Completed"
    #         self.execution.completed_at = datetime.utcnow()
    #         self.db.commit()
    #         log_progress(self.execution_id, f"[LIVE SCRAPING SUCCESS] Generated {contacts_added} valid new leads (Duplicates skipped). Total companies scanned: {companies_added}")

    # And then def _discover_websites...
    
    # Currently it has duplicate code starting from `                # Safety check: if we've tried more times than we have variations + 2, we might be stuck`
    # Let's just find the first instance of `    def _discover_websites(self, query: str, max_results: int) -> list:` and cut everything before it up to the end of the clean for loop.
    
    # We will match the clean end of our for loop
    clean_end_marker = '            log_progress(self.execution_id, f"Valid Leads: {contacts_added}/{target_leads}\\n------------------------------------------------")'
    
    clean_end_idx = content.find(clean_end_marker)
    if clean_end_idx == -1:
        print("Could not find clean end marker")
        return
        
    end_of_clean_end = clean_end_idx + len(clean_end_marker)
    
    # We will match the start of `_discover_websites`
    discover_marker = '    def _discover_websites(self, query: str, max_results: int) -> list:'
    
    # We want to find the LAST occurrence of `_discover_websites` in case it was duplicated? Wait, `_discover_websites` shouldn't be duplicated unless the regex replaced it too.
    discover_idx = content.rfind(discover_marker)
    if discover_idx == -1:
        print("Could not find discover marker")
        return
        
    print(f"Clean end at {end_of_clean_end}, discover at {discover_idx}")
    
    # The middle part is garbage
    middle_garbage = content[end_of_clean_end:discover_idx]
    
    # Replace the middle garbage with the proper method ending
    proper_ending = """

        self.execution.status = "Completed"
        self.execution.completed_at = datetime.utcnow()
        self.db.commit()
        log_progress(self.execution_id, f"[LIVE SCRAPING SUCCESS] Generated {contacts_added} valid new leads (Duplicates skipped). Total companies scanned: {companies_added}")

"""
    
    new_content = content[:end_of_clean_end] + proper_ending + content[discover_idx:]
    
    with open("backend/scraper.py", "w", encoding="utf-8") as f:
        f.write(new_content)
        
    print("Cleanup successful")

cleanup()
