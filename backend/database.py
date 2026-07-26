import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from dotenv import load_dotenv

# Load optional environment variables from .env file
load_dotenv(override=True)

# Check for custom DATABASE_URL (e.g. Supabase Postgres)
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    # SQLAlchemy requires "postgresql://" instead of "postgres://" (Supabase default connection URI scheme)
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    # PostgreSQL does not need check_same_thread
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=300)
else:
    # Fallback to local SQLite database
    DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "leads.db"))
    DATABASE_URL = f"sqlite:///{DB_PATH}"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # User-specific engine behavior settings
    simulation_mode = Column(Boolean, default=False)
    scraping_delay = Column(Float, default=2.0)
    max_search_results = Column(Integer, default=10)

    # User-specific SMTP outreach settings
    smtp_host = Column(String, default="smtp.gmail.com")
    smtp_port = Column(Integer, default=587)
    smtp_username = Column(String, default="")
    smtp_password = Column(String, default="")
    smtp_use_tls = Column(Boolean, default=True)

    # AI Extraction Engine — Groq API (replaces all other LLM/search APIs)
    groq_api_key = Column(String, default="")

    executions = relationship("Execution", back_populates="user", cascade="all, delete-orphan")
    campaigns = relationship("Campaign", back_populates="user", cascade="all, delete-orphan")

class Execution(Base):
    __tablename__ = "executions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False) # Linked to user
    category = Column(String, nullable=False)
    location = Column(String, nullable=False)
    keywords = Column(String, nullable=True)
    status = Column(String, default="Running") # Running, Completed, Failed
    total_found = Column(Integer, default=0)
    valid_leads = Column(Integer, default=0)
    sent_count = Column(Integer, default=0)
    reply_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="executions")
    companies = relationship("Company", back_populates="execution", cascade="all, delete-orphan")

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("executions.id"), nullable=False)
    name = Column(String, nullable=False)
    website = Column(String, nullable=True)
    address = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    linkedin_url = Column(String, default="Not Available")
    social_links = Column(String, default="{}")
    source_attribution = Column(String, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)

    execution = relationship("Execution", back_populates="companies")
    contacts = relationship("Contact", back_populates="company", cascade="all, delete-orphan")

class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    name = Column(String, nullable=False)
    designation = Column(String)
    email = Column(String, nullable=False)
    phone = Column(String)
    linkedin_url = Column(String)

    lead_score = Column(Float, default=0.0)

    email_source = Column(String, default="Not Available")
    contact_source = Column(String, default="Unknown")

    status = Column(String, default="New")
    verification_status = Column(String, default="Unverified")
    score_breakdown = Column(String, default="{}")
    source_attribution = Column(String, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="contacts")
    outreach_logs = relationship("OutreachLog", back_populates="contact", cascade="all, delete-orphan")
    
class OutreachLog(Base):
    __tablename__ = "outreach_logs"

    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False)
    email_subject = Column(Text, nullable=True)
    email_body = Column(Text, nullable=True)
    status = Column(String, nullable=False) # Success, Failed
    response_text = Column(Text, nullable=True)
    sent_at = Column(DateTime, default=datetime.utcnow)

    contact = relationship("Contact", back_populates="outreach_logs")

class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    execution_id = Column(Integer, ForeignKey("executions.id"), nullable=True) # Nullable: can target all uncontacted leads
    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    status = Column(String, default="Running") # Running, Completed, Failed
    sent_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="campaigns")

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
