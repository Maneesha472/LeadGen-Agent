import os

filepath = 'backend/scraper.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update max_search_results default
content = content.replace('"max_search_results": getattr(user, "max_search_results", 10),', '"max_search_results": getattr(user, "max_search_results", 50),')
content = content.replace('"max_search_results": 10,', '"max_search_results": 50,')

# 2. Rename functions
content = content.replace('find_website_ddg', 'find_website_exa')
content = content.replace('find_linkedin_ddg', 'find_linkedin_exa')
content = content.replace('find_company_linkedin_ddg', 'find_company_linkedin_exa')
content = content.replace('find_leader_ddg', 'find_leader_exa')

# 3. Fix LinkedIn Exa queries
old_linkedin_person = 'exa.search(f"LinkedIn profile of {person_name} at {company_name}", num_results=3)'
new_linkedin_person = 'exa.search(f"site:linkedin.com/in/ {person_name} {company_name}", type="keyword", num_results=3)'
content = content.replace(old_linkedin_person, new_linkedin_person)

old_linkedin_company = 'exa.search(f"LinkedIn company page for {company_name}", num_results=3)'
new_linkedin_company = 'exa.search(f"site:linkedin.com/company/ {company_name}", type="keyword", num_results=3)'
content = content.replace(old_linkedin_company, new_linkedin_company)

# 4. Fix log messages in the loop
content = content.replace('Searching DDG for', 'Searching Exa AI for')
content = content.replace('Found via DDG:', 'Found via Exa AI:')
content = content.replace('Querying DuckDuckGo for:', 'Querying Exa AI for:')

# 5. Fix final summary message
old_summary = 'Found {companies_added} companies, generated {contacts_added} valid leads.'
new_summary = 'Generated {contacts_added} valid new leads (Duplicates skipped). Total companies scanned: {companies_added}'
content = content.replace(old_summary, new_summary)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Scraper updated successfully.")
