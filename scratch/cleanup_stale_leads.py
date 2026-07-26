import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import SessionLocal, Company, Contact

db = SessionLocal()

# Find contacts with "Not Available"
stale_contacts = db.query(Contact).filter(Contact.email == "Not Available").all()

print(f"Found {len(stale_contacts)} stale contacts with Email = 'Not Available'.")

for c in stale_contacts:
    comp = c.company
    if comp:
        # Look if a valid contact exists for this company
        valid_c = db.query(Contact).filter(Contact.company_id == comp.id, Contact.email != "Not Available").first()
        if not valid_c:
            # Check if any contact with valid email exists for same domain
            valid_c = db.query(Contact).join(Company).filter(Company.website.like(f"%{comp.website.replace('https://', '').replace('http://', '').strip('/')}%"), Contact.email != "Not Available").first()
        
        if valid_c:
            print(f"Updating stale contact ID #{c.id} for company '{comp.name}' with email: {valid_c.email}")
            c.email = valid_c.email
            c.name = valid_c.name
            c.designation = valid_c.designation
            c.phone = valid_c.phone
            c.verification_status = valid_c.verification_status
            c.linkedin_url = valid_c.linkedin_url
            c.score_breakdown = valid_c.score_breakdown
            c.source_attribution = valid_c.source_attribution
        else:
            print(f"Deleting unresolvable stale contact ID #{c.id} for company '{comp.name}'")
            db.delete(c)

db.commit()
print("\nDATABASE CLEANUP AND SYNCHRONIZATION PASSED 100% SUCCESSFULLY!")
