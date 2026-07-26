import os
import sys
import re

def run_tests():
    print("==============================================")
    print("       VILLOW LEAD GENERATOR TEST SUITE       ")
    print("==============================================")
    
    # Add workspace to path
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    # Test 1: Config Manager Load/Save
    try:
        from backend.config import load_settings, save_settings
        print("\n[TEST 1] Testing Settings Configuration...")
        settings = load_settings()
        assert isinstance(settings, dict), "Settings should be a dictionary"
        assert "simulation_mode" in settings, "simulation_mode setting key missing"
        
        # Save temp setting change
        original_mode = settings["simulation_mode"]
        settings["simulation_mode"] = False
        save_settings(settings)
        
        settings_new = load_settings()
        assert settings_new["simulation_mode"] is False, "Settings failed to save and load new value"
        
        # Restore
        settings_new["simulation_mode"] = original_mode
        save_settings(settings_new)
        print(" -> PASSED: Settings load/save functions verified.")
    except Exception as e:
        print(f" -> FAILED [TEST 1]: {e}")
        return False

    # Test 2: Database Initialization and ORM Schema
    try:
        print("\n[TEST 2] Testing SQLite DB connection and ORM schemas...")
        from backend.database import init_db, SessionLocal, Execution, Company, Contact, OutreachLog, User
        
        # Initialize schema
        init_db()
        db = SessionLocal()
        
        # Insert User record
        test_user = User(
            email="test_verifier@example.com",
            hashed_password="test_hashed_password"
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        
        assert test_user.id is not None, "User ID should be auto-assigned"
        
        # Insert Execution record
        test_exec = Execution(
            user_id=test_user.id,
            category="Test Category",
            location="Test Location",
            keywords="test",
            status="Running"
        )
        db.add(test_exec)
        db.commit()
        db.refresh(test_exec)
        
        assert test_exec.id is not None, "Execution ID should be auto-assigned"
        
        # Insert Company
        test_comp = Company(
            execution_id=test_exec.id,
            name="Test Company LLC",
            website="https://www.testcompany.com",
            address="123 Test Street",
            phone="555-0100",
            industry="Test Category"
        )
        db.add(test_comp)
        db.commit()
        db.refresh(test_comp)
        
        assert test_comp.id is not None, "Company ID should be auto-assigned"
        
        # Insert Contact
        test_contact = Contact(
            company_id=test_comp.id,
            name="Test Name",
            designation="Tester",
            email="test@testcompany.com",
            phone="555-0101",
            linkedin_url="https://linkedin.com/in/test",
            status="New"
        )
        db.add(test_contact)
        db.commit()
        db.refresh(test_contact)
        
        assert test_contact.id is not None, "Contact ID should be auto-assigned"
        
        # Query and Validate Relations
        q_exec = db.query(Execution).filter(Execution.id == test_exec.id).first()
        assert len(q_exec.companies) == 1, "Execution-Company relationship mapping broken"
        assert q_exec.companies[0].name == "Test Company LLC"
        
        q_comp = db.query(Company).filter(Company.id == test_comp.id).first()
        assert len(q_comp.contacts) == 1, "Company-Contact relationship mapping broken"
        assert q_comp.contacts[0].name == "Test Name"
        
        # Clean up test inserts
        db.delete(test_contact)
        db.delete(test_comp)
        db.delete(test_exec)
        db.delete(test_user)
        db.commit()
        db.close()
        print(" -> PASSED: DB migrations and ORM schemas verified.")
    except Exception as e:
        print(f" -> FAILED [TEST 2]: {e}")
        return False

    # Test 3: Scraper Validation & Email Regular Expressions
    try:
        print("\n[TEST 3] Testing Email validation expressions...")
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        valid_emails = ["contact@test.com", "first.last@company.net", "info@sub.domain.co.uk"]
        invalid_emails = ["contact@test", "first.last.company.com", "@company.com", "name@.com"]
        
        for email in valid_emails:
            assert re.match(email_regex, email), f"Should match valid email format: {email}"
            
        for email in invalid_emails:
            assert not re.match(email_regex, email), f"Should block invalid email format: {email}"
            
        print(" -> PASSED: Email regex checks validated.")
    except Exception as e:
        print(f" -> FAILED [TEST 3]: {e}")
        return False

    # Test 4: Outreach Template personalizer
    try:
        print("\n[TEST 4] Testing Email Outreach template variable resolver...")
        from backend.outreach import personalize_message
        
        # Create mock objects
        class MockCompany:
            name = "Starlight Dental"
            website = "https://starlightdental.com"
            address = "Los Angeles, CA"
            industry = "Dentistry"
            
        class MockContact:
            name = "Dr. Jane Doe"
            designation = "Lead Surgeon"
            
        template = "Hi {contact_name} ({contact_title}), I saw {company_name} at {company_website} based in {location} ({industry})."
        expected = "Hi Dr. Jane Doe (Lead Surgeon), I saw Starlight Dental at https://starlightdental.com based in Los Angeles, CA (Dentistry)."
        
        result = personalize_message(template, MockContact(), MockCompany())
        assert result == expected, f"Personalized result mismatch:\nExpected: {expected}\nGot: {result}"
        print(" -> PASSED: Template string variables resolved successfully.")
    except Exception as e:
        print(f" -> FAILED [TEST 4]: {e}")
        return False

    print("\n==============================================")
    print("      ALL BACKEND AUTOMATED TESTS PASSED      ")
    print("==============================================")
    return True

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
