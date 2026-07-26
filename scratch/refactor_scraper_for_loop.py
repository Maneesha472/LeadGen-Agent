import re

def refactor_scraper():
    with open("backend/scraper.py", "r", encoding="utf-8") as f:
        content = f.read()

    # Find where the variables are set up (just before the old while loop)
    setup_match = re.search(r"(        companies_added = 0\n        contacts_added = 0\n.*?        search_variations = \[\]\n        if not is_direct_enrichment:\n.*?                search_variations = \[f\"\{base_query\} \{suffix\}\"\.strip\(\) for suffix in fallback_suffixes\])", content, flags=re.DOTALL)
    
    if not setup_match:
        print("Could not find setup match")
        return
        
    setup_str = setup_match.group(1)
    
    # We want to replace everything from the `while` down to the `search_iteration += 1` at the end
    # Then `        self.execution.status = "Completed"`
    
    # We'll use string replacement. First, extract the old loop.
    old_loop_match = re.search(r"(        while contacts_added < target_leads and companies_added < max_scans:.*?            search_iteration \+= 1)", content, flags=re.DOTALL)
    if not old_loop_match:
        print("Could not find old loop match")
        return
        
    old_loop_str = old_loop_match.group(1)
    
    # New loop structure based on user's pseudo code
    new_loop_str = """        # Iterate through the generated search variations sequentially
        search_iteration = 0
        for search_query in search_variations:
            search_iteration += 1
            if contacts_added >= target_leads or companies_added >= max_scans:
                log_progress(self.execution_id, f"Target reached. Valid Leads: {contacts_added}/{target_leads}. Scanned: {companies_added}/{max_scans}.")
                break
                
            log_progress(self.execution_id, f"\\n------------------------------------------------\\nIteration {search_iteration}/{len(search_variations)}\\nSearching:\\n{search_query}")
            
            websites = []
            
            if is_direct_enrichment and is_url_input:
                if search_iteration > 1: break
                log_progress(self.execution_id, f"[LIVE SCRAPING] Direct Enrichment Mode. Analyzing: {location}")
                parsed = urlparse(location if "://" in location else f"https://{location}")
                domain = parsed.netloc.lower().lstrip("www.")
                full_url = f"{parsed.scheme or 'https'}://{parsed.netloc or domain}"
                if domain not in seen_domains:
                    websites.append({"url": full_url, "name": domain.split(".")[0].capitalize(), "domain": domain})
                    
            elif is_direct_enrichment and not is_url_input:
                if search_iteration > 1: break
                log_progress(self.execution_id, f"[LIVE SCRAPING] Company name: '{location}'. Resolving official website...")
                resolved_url = find_website_exa(location)
                parsed = urlparse(resolved_url)
                domain = parsed.netloc.lower().lstrip("www.")
                log_progress(self.execution_id, f"[LIVE SCRAPING SUCCESS] Resolved: {resolved_url}")
                if domain not in seen_domains:
                    websites.append({"url": resolved_url, "name": location.strip().title(), "domain": domain})
                    
            else:
                new_websites = self._discover_websites(search_query, max_results=30) # Fetch batch
                for site in new_websites:
                    if site["domain"] not in seen_domains:
                        websites.append(site)
                        
            if not websites:
                log_progress(self.execution_id, f"[WARNING] No new target websites found for '{search_query}'. Trying next variation...")
                continue
                
            log_progress(self.execution_id, f"[LIVE SCRAPING] Found {len(websites)} new target websites. Processing batch...")

            # ── Step 2: Scrape each website ─────────────────────────────────────────
            for site in websites:
                if contacts_added >= target_leads or companies_added >= max_scans:
                    break
                    
                domain = site["domain"]
                if domain in seen_domains:
                    continue
                seen_domains.add(domain)
                
                # Increment scanned count before we do any work
                companies_added += 1
                url = site["url"]
                name = site["name"]
                delay = float(self.settings.get("scraping_delay", 2.0))

                log_progress(self.execution_id, f"[LIVE SCRAPING] Visiting {url} ...")
                time.sleep(delay)

                # ── Fetch homepage ──
                home_html = smart_fetch(url, self.execution_id)
                if not home_html:
                    log_progress(self.execution_id, f"[WARNING] Could not load {url}. Skipping.")
                    continue

                # ── Extract from homepage ──
                homepage_emails = extract_emails_from_html(home_html)
                homepage_phone = extract_phone_from_html(home_html)
                socials = extract_social_links(home_html)
                homepage_leaders = extract_leaders_from_html(home_html, url)

                # ── Find & load team page ──
                team_url = find_team_page(home_html, url)
                team_html = ""
                if team_url and team_url != url:
                    log_progress(self.execution_id, f"[LIVE SCRAPING] Team/leadership page found: {team_url}")
                    team_html = smart_fetch(team_url, self.execution_id)
                    if team_html:
                        team_leaders = extract_leaders_from_html(team_html, url)
                        if team_leaders:
                            homepage_leaders = team_leaders  # Team page is more accurate
                        team_emails = extract_emails_from_html(team_html)
                        homepage_emails = list(set(homepage_emails + team_emails))
                        if not homepage_phone:
                            homepage_phone = extract_phone_from_html(team_html)
                        team_socials = extract_social_links(team_html)
                        socials.update({k: v for k, v in team_socials.items() if k not in socials})

                # ── Find & crawl contact subpages ──
                combined_html = home_html + (team_html or "")
                contact_pages = find_contact_subpages(home_html, url, location_hint)

                for cp_url in contact_pages:
                    try:
                        cp_html = fetch_with_requests(cp_url)
                        if not cp_html or len(cp_html) < 500:
                            continue
                        log_progress(self.execution_id, f"[LIVE SCRAPING] Probing subpage: {cp_url}")
                        cp_emails = extract_emails_from_html(cp_html)
                        if cp_emails:
                            homepage_emails = list(set(homepage_emails + cp_emails))
                        if not homepage_phone:
                            homepage_phone = extract_phone_from_html(cp_html)
                        cp_socials = extract_social_links(cp_html)
                        socials.update({k: v for k, v in cp_socials.items() if k not in socials})
                        combined_html += cp_html
                        time.sleep(0.5)
                    except Exception:
                        pass

                # ── AI extraction via Groq ──
                page_text = BeautifulSoup(combined_html[:12000], "html.parser").get_text(separator=" ", strip=True)

                # Build search snippets from leaders found
                leader_info = ""
                if homepage_leaders:
                    leader_info = " | ".join([f"{l['name']} ({l['title']})" for l in homepage_leaders[:5]])

                llm_result = None
                if groq_key:
                    log_progress(self.execution_id, "[LIVE SCRAPING] Groq AI extraction active. Analyzing page data...")
                    llm_result = ExtractorService.extract_decision_maker(page_text, leader_info, groq_key)
                
                if llm_result:
                    contact_name = llm_result.get("name", "Not Available")
                    designation = llm_result.get("designation", "Not Available")
                    person_linkedin = llm_result.get("person_linkedin_url", "Not Available")
                else:
                    contact_name = homepage_leaders[0]["name"] if homepage_leaders else "Office Manager"
                    designation = homepage_leaders[0]["title"] if homepage_leaders else "Operations"
                    person_linkedin = "Not Available"

                if contact_name != "Office Manager" and contact_name != "Not Available":
                    log_progress(self.execution_id, f"[LIVE SCRAPING] Extracted Leader: {contact_name} ({designation})")

                # If missing person_linkedin, query Exa for it
                if contact_name and contact_name not in ("Office Manager", "Not Available", "NOT_FOUND") and person_linkedin == "Not Available":
                    log_progress(self.execution_id, f"[LIVE SCRAPING] Searching LinkedIn for {contact_name} at {name}...")
                    found_li = find_linkedin_exa(name, contact_name)
                    if found_li:
                        person_linkedin = found_li
                        log_progress(self.execution_id, f"[LIVE SCRAPING] Found via Exa AI: {found_li}")

                # If still missing company_linkedin, check DB or query Exa
                company_linkedin = socials.get("company_linkedin", "Not Available")
                if company_linkedin == "Not Available":
                    log_progress(self.execution_id, f"[LIVE SCRAPING] Searching LinkedIn company page for {name}...")
                    c_li = find_company_linkedin_exa(name)
                    if c_li:
                        company_linkedin = c_li
                        log_progress(self.execution_id, f"[LIVE SCRAPING] Found via Exa AI: {c_li}")

                # Format Phone
                phone = format_phone_number(homepage_phone) if homepage_phone else "Not Available"
                address = location

                # ── Pick best email ──
                selected_email = None
                email_source = "Not Available"
                if llm_result and llm_result.get("email"):
                    selected_email = llm_result.get("email")
                    email_source = "Groq LLM Context Analysis"
                elif homepage_emails:
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

                # ── Validate email format (with MX deliverability check) ──
                verification_status = "Unverified"
                if selected_email and selected_email != "Not Available":
                    try:
                        validate_email(selected_email, check_deliverability=True)
                        verification_status = "Valid"
                    except EmailNotValidError:
                        verification_status = "Invalid"

                # ── Build social links JSON ──
                social_links_json = {
                    "facebook": socials.get("facebook", ""),
                    "twitter": socials.get("twitter", ""),
                    "instagram": socials.get("instagram", ""),
                    "youtube": socials.get("youtube", ""),
                }

                # ── Multi-point verification metrics ──
                email_domain_match = False
                if selected_email and selected_email != "Not Available":
                    ed = selected_email.split('@')[-1].lower()
                    wd = domain.lower()
                    if wd in ed or ed in wd:
                        email_domain_match = True

                page_verification_level = 0
                if contact_name and contact_name != "Office Manager":
                    if (team_html and contact_name in team_html) or (contact_name in (cp_html if 'cp_html' in locals() else "")):
                        page_verification_level = 2
                    elif contact_name in home_html:
                        page_verification_level = 1

                linkedin_verified = False
                if person_linkedin and person_linkedin != "Not Available":
                    name_parts = [p.lower() for p in contact_name.split() if len(p) > 2]
                    if name_parts and any(p in person_linkedin.lower() for p in name_parts):
                        linkedin_verified = True

                # ── Score the lead ──
                score_data = ScoringService.calculate_lead_score(
                    contact_name=contact_name,
                    designation=designation,
                    email=selected_email,
                    phone=phone,
                    comp_linkedin=company_linkedin,
                    person_linkedin=person_linkedin,
                    company_name=name,
                    website=url,
                    address=address,
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

                # --- FINAL VALIDATION GAUNTLET ---
                reject_reason = None

                # ✓ Person exists
                if not contact_name or contact_name in ("Office Manager", "Not Available", "null", "NOT_FOUND"):
                    reject_reason = "Person exists check failed"
                # ✓ Real title
                elif not designation or designation in ("Not Available", "null", "Operations"):
                    reject_reason = "Real title check failed"
                # ✓ Official email & Email domain matches
                elif not selected_email or selected_email == "Not Available" or not email_domain_match:
                    reject_reason = "Email verification check failed (missing or domain mismatch)"
                # ✓ LinkedIn matches
                elif not linkedin_verified:
                    reject_reason = "LinkedIn match check failed"
                # ✓ Website exists
                elif not url:
                    reject_reason = "Website exists check failed"
                # ✓ Confidence >= 80
                elif score_data['total_score'] < 80:
                    reject_reason = f"Confidence score ({score_data['total_score']}) < 80"
                # ✓ Email Verification Status
                elif verification_status != "Valid":
                    reject_reason = "Email is unverified or missing (MX Record Failed)"

                if reject_reason:
                    log_progress(self.execution_id, f"[QUALITY FILTER] Lead for {name} rejected: {reject_reason}")
                    continue
                # ---------------------------------

                # ── Save Company record ──
                company = Company(
                    execution_id=self.execution_id,
                    name=name,
                    website=url,
                    address=address,
                    phone=phone,
                    industry=category,
                    linkedin_url=company_linkedin,
                    social_links=json.dumps(social_links_json),
                    source_attribution=json.dumps(source_map),
                )
                self.db.add(company)
                self.db.commit()
                self.db.refresh(company)

                # ── Save Contact record ──
                contact = Contact(
                    company_id=company.id,
                    name=contact_name,
                    designation=designation,
                    email=selected_email,
                    phone=phone,
                    linkedin_url=person_linkedin,
                    status="New",
                    verification_status=verification_status,
                    score_breakdown=json.dumps(score_data.get("breakdown", {})),
                    source_attribution=json.dumps(source_map),
                )
                self.db.add(contact)
                self.db.commit()
                contacts_added += 1
                breakdown_str = ", ".join([f"{k}: {v}" for k, v in score_data.get("breakdown", {}).items()])
                log_progress(self.execution_id, f"[SUCCESS] Saved lead for {name}: {contact_name} ({designation}) | Verified: {verification_status} | Score Breakdown: {breakdown_str}")

                self.execution.total_found = companies_added
                self.execution.valid_leads = contacts_added
                self.db.commit()

            # End of processing batch, report stats
            log_progress(self.execution_id, f"Valid Leads: {contacts_added}/{target_leads}\\n------------------------------------------------")"""
            
    content = content.replace(old_loop_str, new_loop_str)

    with open("backend/scraper.py", "w", encoding="utf-8") as f:
        f.write(content)

    print("Replaced logic with precise user-defined pseudo code.")

refactor_scraper()
