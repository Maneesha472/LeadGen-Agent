import re

def refactor_scraper():
    with open("backend/scraper.py", "r", encoding="utf-8") as f:
        content = f.read()

    # Find the _run_live_scraping function body start
    start_match = re.search(r"    def _run_live_scraping\(self\):\n.*?        log_progress\(self\.execution_id, \"\[LIVE SCRAPING\] Starting live scraper with Leader Agent pipeline\.\.\.\"\)\n        time\.sleep\(0\.5\)", content, flags=re.DOTALL)
    
    # We will replace the entire _run_live_scraping function
    # It ends before `def _discover_websites`
    func_match = re.search(r"    def _run_live_scraping\(self\):(.*?)    def _discover_websites", content, flags=re.DOTALL)
    if not func_match:
        print("Could not find function")
        return
        
    old_body = func_match.group(1)
    
    # Let's extract everything inside the `for site in websites:` loop to reuse it
    loop_match = re.search(r"        for site in websites:\n(.*?)        self\.execution\.status = \"Completed\"", old_body, flags=re.DOTALL)
    if not loop_match:
        print("Could not find for loop")
        return
        
    inner_loop = loop_match.group(1)
    
    # Re-indent the inner loop
    # Wait, the inner loop handles `delay = float(self.settings.get("scraping_delay", 2.0))` etc.
    # We just need to add `if contacts_added >= target_leads or companies_scanned >= max_scans: break` at the start of the loop
    # and change the counters.

    # Instead of regex magic which is fragile for 400 lines of code, let's just do a string replacement of the specific chunks.

    # 1. Replace the initial setup and website discovery part
    setup_old = """        # Extract optional location hint from keywords
        location_hint = ""
        if keywords and "Location:" in keywords:
            m = re.search(r'Location:\s*([^|]+)', keywords)
            if m:
                location_hint = m.group(1).strip()

        # ── Step 1: Build website list ──────────────────────────────────────────
        websites = []
        is_direct_enrichment = (category == "Direct Enrichment")
        is_url_input = ("." in location or "http" in location)

        if is_direct_enrichment and is_url_input:
            # Direct URL/domain input → enrich that one site
            log_progress(self.execution_id, f"[LIVE SCRAPING] Direct Enrichment Mode. Analyzing: {location}")
            parsed = urlparse(location if "://" in location else f"https://{location}")
            domain = parsed.netloc.lower().lstrip("www.")
            full_url = f"{parsed.scheme or 'https'}://{parsed.netloc or domain}"
            websites.append({"url": full_url, "name": domain.split(".")[0].capitalize(), "domain": domain})

        elif is_direct_enrichment and not is_url_input:
            # Company name typed in Direct Enrichment → resolve its website
            log_progress(self.execution_id, f"[LIVE SCRAPING] Company name: '{location}'. Resolving official website...")
            resolved_url = find_website_exa(location)
            parsed = urlparse(resolved_url)
            domain = parsed.netloc.lower().lstrip("www.")
            log_progress(self.execution_id, f"[LIVE SCRAPING SUCCESS] Resolved: {resolved_url}")
            websites.append({"url": resolved_url, "name": location.strip().title(), "domain": domain})

        # For ALL Bulk Search runs (city/region + business category): go to discovery
        if not websites:
            query = f"{category} companies in {location}"
            if keywords:
                query += f" {keywords}"
            log_progress(self.execution_id, f"[LIVE SCRAPING] Querying Exa AI for: '{query}'")
            websites = self._discover_websites(query, max_results)

        if not websites:
            log_progress(self.execution_id, "[WARNING] No target websites found. Execution complete with 0 leads.")
            self.execution.status = "Completed"
            self.execution.completed_at = datetime.utcnow()
            self.db.commit()
            return

        log_progress(self.execution_id, f"[LIVE SCRAPING] Found {len(websites)} target websites. Scraping details...")

        # ── Step 2: Scrape each website ─────────────────────────────────────────
        companies_added = 0
        contacts_added = 0

        for site in websites:"""

    setup_new = """        target_leads = max_results # The user requests a number of valid leads, currently passed as max_search_results
        max_scans = 200
        
        # Extract optional location hint from keywords
        location_hint = ""
        if keywords and "Location:" in keywords:
            m = re.search(r'Location:\s*([^|]+)', keywords)
            if m:
                location_hint = m.group(1).strip()

        is_direct_enrichment = (category == "Direct Enrichment")
        is_url_input = ("." in location or "http" in location)
        
        companies_added = 0
        contacts_added = 0
        search_iteration = 0
        seen_domains = set()

        while contacts_added < target_leads and companies_added < max_scans:
            # ── Step 1: Build website list ──────────────────────────────────────────
            websites = []
            
            if is_direct_enrichment and is_url_input:
                if search_iteration > 0: break
                log_progress(self.execution_id, f"[LIVE SCRAPING] Direct Enrichment Mode. Analyzing: {location}")
                parsed = urlparse(location if "://" in location else f"https://{location}")
                domain = parsed.netloc.lower().lstrip("www.")
                full_url = f"{parsed.scheme or 'https'}://{parsed.netloc or domain}"
                if domain not in seen_domains:
                    websites.append({"url": full_url, "name": domain.split(".")[0].capitalize(), "domain": domain})
            
            elif is_direct_enrichment and not is_url_input:
                if search_iteration > 0: break
                log_progress(self.execution_id, f"[LIVE SCRAPING] Company name: '{location}'. Resolving official website...")
                resolved_url = find_website_exa(location)
                parsed = urlparse(resolved_url)
                domain = parsed.netloc.lower().lstrip("www.")
                log_progress(self.execution_id, f"[LIVE SCRAPING SUCCESS] Resolved: {resolved_url}")
                if domain not in seen_domains:
                    websites.append({"url": resolved_url, "name": location.strip().title(), "domain": domain})
            
            else:
                base_query = f"{category} companies in {location}"
                if keywords:
                    base_query += f" {keywords}"
                
                # Cycle through variations to discover fresh domains
                variations = ["", "B2B", "services", "technology", "enterprise", "top rated", "providers"]
                var_suffix = f" {variations[search_iteration % len(variations)]}" if search_iteration > 0 else ""
                query = base_query + var_suffix
                
                log_progress(self.execution_id, f"[LIVE SCRAPING] Querying Exa AI for: '{query}'")
                new_websites = self._discover_websites(query, max_results=30) # Fetch batch
                
                for site in new_websites:
                    if site["domain"] not in seen_domains:
                        websites.append(site)
            
            if not websites:
                if search_iteration == 0:
                    log_progress(self.execution_id, "[WARNING] No target websites found. Execution complete.")
                else:
                    log_progress(self.execution_id, "[WARNING] No more new websites found via Exa search.")
                break
                
            log_progress(self.execution_id, f"[LIVE SCRAPING] Found {len(websites)} new target websites. Scraping details (Iteration {search_iteration+1})...")

            # ── Step 2: Scrape each website ─────────────────────────────────────────
            for site in websites:
                if contacts_added >= target_leads or companies_added >= max_scans:
                    log_progress(self.execution_id, f"Reached limit. Valid Leads: {contacts_added}/{target_leads}. Scanned: {companies_added}/{max_scans}.")
                    break
                    
                domain = site["domain"]
                if domain in seen_domains:
                    continue
                seen_domains.add(domain)
                
                # Increment scanned count before we do any work
                companies_added += 1"""
                
    content = content.replace(setup_old, setup_new)
    
    # 2. Add an extra indent to the whole inner loop... wait, no. The new code is still inside `while ...` and `for site in websites:`. 
    # But Python indentation needs to match.
    # Actually, the original loop was:
    #         for site in websites:
    #             ...
    # The new loop is also:
    #         while ...:
    #             for site in websites:
    #                 ...
    # Wait, the `while` is 2 indents (8 spaces). The `for` is 3 indents (12 spaces).
    # In the original, the `for` is 2 indents (8 spaces).
    # This means everything inside the `for` needs to be indented by 4 spaces.
    
    # Let's fix the indentation of everything after the new setup.
    # Find the chunk starting from `url = site["url"]` down to `self.db.commit()` at the end of the `for` loop.
    
    for_body_match = re.search(r"(\n        url = site\[\"url\"\].*?            self\.db\.commit\(\))", content, flags=re.DOTALL)
    if for_body_match:
        for_body = for_body_match.group(1)
        
        # Indent every line by 4 spaces
        new_for_body = "\n".join("    " + line if line.strip() else line for line in for_body.split("\n"))
        
        content = content.replace(for_body, new_for_body)
    
    # 3. Add `search_iteration += 1` at the end of the `while` loop
    # The end of the `for` loop is `                self.db.commit()`
    # And after it we have:
    #         self.execution.status = "Completed"
    
    # We replace:
    end_old = """                self.db.commit()

        self.execution.status = "Completed\""""
        
    end_new = """                self.db.commit()
            
            search_iteration += 1

        self.execution.status = "Completed\""""
    content = content.replace(end_old, end_new)
    
    with open("backend/scraper.py", "w", encoding="utf-8") as f:
        f.write(content)
        
    print("Successfully refactored backend/scraper.py")

refactor_scraper()
