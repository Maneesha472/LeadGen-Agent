import re

def refactor_scraper():
    with open('backend/scraper.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # We will replace the entire _run_live_scraping method with a new concurrent version
    # The original _run_live_scraping starts at line 1060 (approx) and ends at the end of the class.
    
    match = re.search(r'(    def _run_live_scraping\(self\):.*)', content, flags=re.DOTALL)
    if not match:
        print("Could not find _run_live_scraping")
        return
    
    new_method = """    def _process_website(self, site: dict, location_hint: str, groq_key: str, category: str, location: str):
        domain = site["domain"]
        url = site["url"]
        name = site["name"]
        
        log_progress(self.execution_id, f"[LIVE SCRAPING] Visiting {url} ...")
        
        # ── Fetch homepage ──
        home_html = smart_fetch(url, self.execution_id)
        if not home_html:
            log_progress(self.execution_id, f"[WARNING] Could not load {url}. Skipping.")
            return None
            
        homepage_emails = extract_emails_from_html(home_html)
        homepage_phone = extract_phone_from_html(home_html)
        socials = extract_social_links(home_html)
        homepage_leaders = extract_leaders_from_html(home_html, url)
        
        # Clean DOM for text extraction
        def clean_and_extract(html):
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.extract()
            return soup.get_text(separator=" ", strip=True)
            
        page_text = clean_and_extract(home_html)[:6000]
        
        team_url = find_team_page(home_html, url)
        team_html = ""
        if team_url and team_url != url:
            log_progress(self.execution_id, f"[LIVE SCRAPING] Team/leadership page found: {team_url}")
            team_html = smart_fetch(team_url, self.execution_id)
            if team_html:
                team_leaders = extract_leaders_from_html(team_html, url)
                if team_leaders:
                    homepage_leaders = team_leaders
                homepage_emails = list(set(homepage_emails + extract_emails_from_html(team_html)))
                if not homepage_phone:
                    homepage_phone = extract_phone_from_html(team_html)
                socials.update({k: v for k, v in extract_social_links(team_html).items() if k not in socials})
                page_text += " " + clean_and_extract(team_html)[:3000]
                
        contact_pages = find_contact_subpages(home_html, url, location_hint)
        for cp_url in contact_pages:
            try:
                cp_html = smart_fetch(cp_url, self.execution_id)
                if not cp_html or len(cp_html) < 500:
                    continue
                log_progress(self.execution_id, f"[LIVE SCRAPING] Probing subpage: {cp_url}")
                homepage_emails = list(set(homepage_emails + extract_emails_from_html(cp_html)))
                if not homepage_phone:
                    homepage_phone = extract_phone_from_html(cp_html)
                socials.update({k: v for k, v in extract_social_links(cp_html).items() if k not in socials})
                page_text += " " + clean_and_extract(cp_html)[:3000]
            except Exception:
                pass
                
        # ── AI extraction via Groq ──
        leader_info = ""
        if homepage_leaders:
            leader_info = " | ".join([f"{l['name']} ({l['title']})" for l in homepage_leaders[:5]])
            
        llm_result = None
        if groq_key:
            log_progress(self.execution_id, "[LIVE SCRAPING] Groq AI extraction active. Analyzing page data...")
            llm_result = ExtractorService.extract_with_llm(page_text, leader_info, groq_key)
            
        if llm_result:
            contact_name = llm_result.get("contact_name", "Not Available")
            designation = llm_result.get("designation", "Not Available")
            person_linkedin = llm_result.get("person_linkedin_url", "Not Available")
        else:
            contact_name = homepage_leaders[0]["name"] if homepage_leaders else "Office Manager"
            designation = homepage_leaders[0]["title"] if homepage_leaders else "Operations"
            person_linkedin = "Not Available"
            
        if contact_name and contact_name not in ("Office Manager", "Not Available", "NOT_FOUND") and person_linkedin == "Not Available":
            log_progress(self.execution_id, f"[LIVE SCRAPING] Searching LinkedIn for {contact_name} at {name} (Waterfall)...")
            found_li = find_linkedin_waterfall(contact_name, name, self.execution_id)
            if found_li and found_li != "Not Available":
                person_linkedin = found_li
                
        company_linkedin = socials.get("company_linkedin", "Not Available")
        if company_linkedin == "Not Available":
            log_progress(self.execution_id, f"[LIVE SCRAPING] Searching LinkedIn company page for {name} in {location}...")
            c_li = find_company_linkedin_exa(name, location, domain, category, groq_key)
            if c_li:
                company_linkedin = c_li
                log_progress(self.execution_id, f"[LIVE SCRAPING] Found via Exa AI: {c_li}")
                
        phone = homepage_phone.strip() if homepage_phone else "Not Available"
        
        selected_email = None
        email_source = "Not Available"
        if llm_result and llm_result.get("email"):
            selected_email = llm_result.get("email")
            email_source = "Groq LLM Context Analysis"
        elif homepage_emails:
            homepage_emails.sort(key=lambda e: score_email(e), reverse=True)
            personal_emails = [e for e in homepage_emails if is_personal_email(e, contact_name)]
            if personal_emails:
                selected_email = personal_emails[0]
                email_source = "Website DOM Extraction (Personal)"
            else:
                selected_email = homepage_emails[0]
                email_source = "Website DOM Extraction (Best Match)"
                
        if not selected_email or score_email(selected_email) < 40:
            generic_emails = [e for e in homepage_emails if e and score_email(e) < 40]
            if generic_emails:
                selected_email = generic_emails[0]
                email_source = "Website DOM Extraction (Generic)"
            else:
                selected_email = selected_email or f"contact@{domain}"
                
        verification_status = "Unverified"
        if selected_email and selected_email != "Not Available":
            try:
                validate_email(selected_email, check_deliverability=True)
                verification_status = "Valid"
            except EmailNotValidError:
                try:
                    validate_email(selected_email, check_deliverability=False)
                    verification_status = "Syntax Valid"
                except EmailNotValidError:
                    verification_status = "Invalid"
                    
        email_domain_match = False
        if selected_email and selected_email != "Not Available":
            ed = selected_email.split('@')[-1].lower()
            wd = domain.lower()
            generic_domains = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com"]
            if ed not in generic_domains and (ed == wd or wd.endswith(f".{ed}") or ed.endswith(f".{wd}")):
                email_domain_match = True
                
        page_verification_level = 0
        if contact_name and contact_name != "Office Manager":
            if (team_html and contact_name in team_html) or (contact_name in page_text):
                page_verification_level = 2
            elif contact_name in home_html:
                page_verification_level = 1
                
        linkedin_verified = False
        if person_linkedin and person_linkedin != "Not Available":
            name_parts = [p.lower() for p in contact_name.split() if len(p) > 2]
            if name_parts and any(p in person_linkedin.lower() for p in name_parts):
                linkedin_verified = True
                
        score_data = ScoringService.calculate_lead_score(
            contact_name=contact_name,
            designation=designation,
            email=selected_email,
            phone=phone,
            comp_linkedin=company_linkedin,
            person_linkedin=person_linkedin,
            company_name=name,
            website=url,
            address=location,
            verification_status=verification_status,
            email_domain_match=email_domain_match,
            page_verification_level=page_verification_level,
            linkedin_verified=linkedin_verified
        )
        
        person_li_source = "Not Available"
        if person_linkedin != "Not Available":
            person_li_source = "Website DOM / Groq AI" if socials.get("person_linkedin") or (llm_result and llm_result.get("person_linkedin_url")) else "DuckDuckGo Search Engine"
            
        source_map = {
            "email": email_source,
            "phone": "tel: link / Page Footer" if homepage_phone else "Not Available",
            "company_linkedin": "Website DOM" if socials.get("company_linkedin") else "Not Available",
            "person_linkedin": person_li_source,
            "discovery": "Exa Neural Search + Playwright Browser",
        }
        
        log_progress(self.execution_id, f"[LIVE SCRAPING] Processing lead for {name} | Email: {selected_email} | Score: {score_data['total_score']}/100")
        
        reject_reason = None
        is_company_lead = False
        if not contact_name or contact_name in ("Office Manager", "Not Available", "null", "NOT_FOUND"):
            is_company_lead = True
            
        if not selected_email or selected_email == "Not Available" or not email_domain_match:
            reject_reason = "Email verification check failed (missing or domain mismatch)"
        elif verification_status != "Valid":
            reject_reason = "Email is unverified (MX Record Failed)"
        elif not url:
            reject_reason = "Website exists check failed"
        elif score_data['total_score'] < 80:
            reject_reason = f"Confidence score ({score_data['total_score']}) < 80"
        elif not is_company_lead:
            if not designation or designation in ("Not Available", "null", "Operations"):
                reject_reason = "Real title check failed for person-level lead"
            elif not linkedin_verified:
                reject_reason = "LinkedIn match check failed for person-level lead"
                
        if reject_reason:
            log_progress(self.execution_id, f"[QUALITY FILTER] Lead for {name} rejected: {reject_reason}")
            return None
            
        # Return valid lead data
        social_links_json = {
            "facebook": socials.get("facebook", ""),
            "twitter": socials.get("twitter", ""),
            "instagram": socials.get("instagram", ""),
            "youtube": socials.get("youtube", ""),
        }
        return {
            "name": name,
            "url": url,
            "address": location,
            "phone": phone,
            "category": category,
            "company_linkedin": company_linkedin,
            "social_links_json": social_links_json,
            "source_map": source_map,
            "contact_name": contact_name,
            "designation": designation,
            "selected_email": selected_email,
            "score_data": score_data
        }

    def _run_live_scraping(self):
        log_progress(self.execution_id, "[LIVE SCRAPING] Starting live scraper with Enterprise Concurrency pipeline...")
        time.sleep(0.5)
        
        category = self.execution.category.strip()
        location = self.execution.location.strip()
        keywords = self.execution.keywords.strip() if self.execution.keywords else ""
        groq_key = os.getenv("GROQ_API_KEY", self.settings.get("groq_api_key", ""))
        max_results = int(self.settings.get("max_search_results", 50))
        target_leads = max_results
        max_scans = 200
        
        location_hint = ""
        if keywords and "Location:" in keywords:
            m = re.search(r"Location:\s*([^|]+)", keywords)
            if m:
                location_hint = m.group(1).strip()
                
        is_direct_enrichment = category == "Direct Enrichment"
        search_variations = []
        if not is_direct_enrichment:
            log_progress(self.execution_id, "[LIVE SCRAPING] Generating semantic search variations via Groq AI...")
            search_variations = ExtractorService.generate_search_variations(category, location, keywords, groq_key)
            if search_variations:
                search_variations = search_variations[:3]
                log_progress(self.execution_id, f"[LIVE SCRAPING] Generated {len(search_variations)} search variations (Capped at 3).")
            else:
                base_query = f"{category} companies in {location}"
                if keywords:
                    base_query += f" {keywords}"
                search_variations = [base_query]
        else:
            search_variations = [f"{keywords}"]
            
        companies_added = 0
        contacts_added = 0
        seen_domains = set()
        
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading
        
        db_lock = threading.Lock()
        
        for iteration, search_query in enumerate(search_variations, start=1):
            if contacts_added >= target_leads or companies_added >= max_scans:
                break
                
            log_progress(self.execution_id, f"Iteration {iteration}/{len(search_variations)}\\nSearching: {search_query}")
            
            exa = get_exa_client()
            websites = []
            if exa:
                try:
                    res = exa.search_and_contents(search_query, type="keyword", num_results=20, text=True)
                    for r in res.results:
                        if not r.url: continue
                        domain_parsed = urlparse(r.url).netloc.lower().replace("www.", "")
                        if any(b in domain_parsed for b in BLOCKED_DOMAINS):
                            continue
                        websites.append({"url": r.url, "name": r.title or domain_parsed, "domain": domain_parsed})
                except Exception as e:
                    log_progress(self.execution_id, f"[WARNING] Exa search failed: {e}")
                    
            if not websites:
                continue
                
            log_progress(self.execution_id, f"[LIVE SCRAPING] Found {len(websites)} new target websites. Processing batch concurrently...")
            
            # Use ThreadPoolExecutor for concurrent fetching and extraction
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {}
                for site in websites:
                    if contacts_added >= target_leads or companies_added >= max_scans:
                        break
                    domain = site["domain"]
                    with db_lock:
                        if domain in seen_domains:
                            continue
                        seen_domains.add(domain)
                        companies_added += 1
                        
                    future = executor.submit(self._process_website, site, location_hint, groq_key, category, location)
                    futures[future] = site
                    
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        with db_lock:
                            from .scraper import normalize_url
                            normalized_site_url = normalize_url(result["url"])
                            existing_company = self.db.query(Company).filter(Company.website == normalized_site_url).first()
                            
                            if existing_company:
                                log_progress(self.execution_id, f"[DUPLICATE] Company already processed: {result['url']}")
                                continue
                                
                            company = Company(
                                execution_id=self.execution_id,
                                name=result["name"],
                                website=normalized_site_url,
                                address=result["address"],
                                phone=result["phone"],
                                industry=result["category"],
                                linkedin_url=result["company_linkedin"],
                                social_links=json.dumps(result["social_links_json"]),
                                source_attribution=json.dumps(result["source_map"]),
                            )
                            self.db.add(company)
                            self.db.flush()
                            self.db.refresh(company)
                            
                            existing_contact = (
                                self.db.query(Contact)
                                .join(Company, Contact.company_id == Company.id)
                                .filter(Contact.email == result["selected_email"])
                                .first()
                            )
                            
                            if existing_contact:
                                log_progress(self.execution_id, f"[DUPLICATE] Contact already processed: {result['selected_email']}")
                                continue
                                
                            contact = Contact(
                                company_id=company.id,
                                name=result["contact_name"],
                                designation=result["designation"],
                                email=result["selected_email"],
                                linkedin_url=result["score_data"].get("person_linkedin"),
                                confidence_score=result["score_data"]["total_score"],
                                verification_status="Verified",
                                breakdown=json.dumps(result["score_data"].get("breakdown", {}))
                            )
                            self.db.add(contact)
                            self.db.flush()
                            contacts_added += 1
                            log_progress(self.execution_id, f"[SAVED] Lead {result['contact_name']} @ {result['name']} saved to database.")
                            
            self.db.commit() # Batch commit after each chunk of websites finishes
            
        self.db.commit()
        if self.execution:
            self.execution.status = "Completed"
            self.execution.completed_at = datetime.utcnow()
            self.db.commit()
"""
    
    # We must insert this new code replacing everything from `def _run_live_scraping(self):`
    # till the end of the file.
    new_content = content[:match.start(1)] + new_method + "\n"
    
    with open('backend/scraper.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("Successfully refactored _run_live_scraping to use ThreadPoolExecutor and batch commits!")

if __name__ == "__main__":
    refactor_scraper()
