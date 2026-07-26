import os
import re

with open('backend/scraper.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace existing_company lookup
old_lookup = """                existing_company = (
                    self.db.query(Company)
                    .filter(
                        Company.execution_id == self.execution_id,
                        Company.website == url
                    )
                    .first()
                )"""

new_lookup = """                normalized_site_url = normalize_url(url)
                existing_company = (
                    self.db.query(Company)
                    .filter(
                        Company.execution_id == self.execution_id,
                        Company.website == normalized_site_url
                    )
                    .first()
                )"""
content = content.replace(old_lookup, new_lookup)

old_company = """                company = Company(
                    execution_id=self.execution_id,
                    name=name,
                    website=url,
                    address=address,
                    phone=phone,
                    industry=category,
                    linkedin_url=company_linkedin,
                    social_links=json.dumps(social_links_json),
                    source_attribution=json.dumps(source_map),
                )"""
new_company = """                company = Company(
                    execution_id=self.execution_id,
                    name=name,
                    website=normalized_site_url,
                    address=address,
                    phone=phone,
                    industry=category,
                    linkedin_url=company_linkedin,
                    social_links=json.dumps(social_links_json),
                    source_attribution=json.dumps(source_map),
                )"""
content = content.replace(old_company, new_company)

old_commit_1 = """                self.db.add(company)
                self.db.commit()
                self.db.refresh(company)"""
new_commit_1 = """                self.db.add(company)
                self.db.flush()  # Use flush instead of commit inside the loop"""
content = content.replace(old_commit_1, new_commit_1)

old_commit_2 = """                self.db.add(contact)
                self.db.commit()"""
new_commit_2 = """                self.db.add(contact)
                self.db.flush()  # Use flush inside the loop"""
content = content.replace(old_commit_2, new_commit_2)

old_commit_3 = """                self.db.commit()
                
                log_progress(self.execution_id, f"[SAVED] Lead {contact_name} @ {name} saved to database.")"""
new_commit_3 = """                self.db.commit()  # Batch commit at the end of lead processing
                
                log_progress(self.execution_id, f"[SAVED] Lead {contact_name} @ {name} saved to database.")"""
content = content.replace(old_commit_3, new_commit_3)

# ensure we commit outside the loop if anything is left.
old_outer_loop = """            if contacts_added >= target_leads or companies_added >= max_scans:
                log_progress(self.execution_id, f"Target reached. Valid Leads: {contacts_added}/{target_leads}. Scanned: {companies_added}/{max_scans}.")
                break"""
new_outer_loop = """            if contacts_added >= target_leads or companies_added >= max_scans:
                self.db.commit()
                log_progress(self.execution_id, f"Target reached. Valid Leads: {contacts_added}/{target_leads}. Scanned: {companies_added}/{max_scans}.")
                break"""
content = content.replace(old_outer_loop, new_outer_loop)

# End of function
content = content.replace("        self.execution.completed_at = datetime.utcnow()\n        self.db.commit()", "        self.execution.completed_at = datetime.utcnow()\n        self.db.commit()\n        self.db.flush()")

with open('backend/scraper.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Phase 4 applied via script")
