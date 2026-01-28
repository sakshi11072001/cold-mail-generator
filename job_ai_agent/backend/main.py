from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, BackgroundTasks
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey , DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from passlib.context import CryptContext
from pydantic import BaseModel
import hashlib
import json

# Import your custom services
from backend.resume_parser import parser_service
from backend.scraper import job_scraper  # Make sure you have scraper.py in the same folder
from backend.mailer import mail_service
# Database Setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./jobs_app.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Password Hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_clean_password(raw_password: str) -> str:
    return hashlib.sha256(raw_password.encode("utf-8")).hexdigest()

# --- DATABASE MODELS ---

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    skills = Column(String) 
    experience = Column(Integer)

class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    company = Column(String)
    link = Column(String)
    required_skills = Column(String)
    required_experience = Column(String)
    email = Column(String, nullable=True)
    status = Column(String, default="found") 
    date_applied = Column(DateTime, nullable=True)

Base.metadata.create_all(bind=engine)

# --- SCHEMAS ---
class UserCreate(BaseModel):
    email: str
    password: str

# --- FASTAPI APP ---
app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- AUTH ROUTES ---

@app.post("/signup")
def signup(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    prepared_pw = get_clean_password(user.password)
    hashed_pwd = pwd_context.hash(prepared_pw)
    new_user = User(email=user.email, hashed_password=hashed_pwd)
    db.add(new_user)
    db.commit()
    return {"message": "User created successfully"}

@app.post("/login")
def login(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    prepared_pw = get_clean_password(user.password)
    if not db_user or not pwd_context.verify(prepared_pw, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"message": "Login successful", "email": db_user.email}

# --- RESUME ROUTE ---

@app.post("/upload-resume")
async def upload_resume(email: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    file_bytes = await file.read()
    parsed_info = parser_service.parse(file_bytes)
    
    user.skills = ", ".join(parsed_info["skills"])
    user.experience = parsed_info["experience"]
    db.commit()
    
    return {
        "message": "Resume parsed",
        "skills": parsed_info["skills"],
        "experience": parsed_info["experience"]
    }


# backend/main.py (Ensure your background task handles the email)

async def run_scraping_logic(user_id: int, skills_str: str, experience: int):
    db = SessionLocal()
    try:
        skills_list = [s.strip() for s in skills_str.split(",")]
        found_jobs = await job_scraper.search_jobs(skills_list, experience)
        
        for j in found_jobs:
            exists = db.query(Job).filter(Job.link == j['link']).first()
            if not exists:
                new_job = Job(
                    user_id=user_id,
                    title=j['title'],
                    company=j['company'],
                    link=j['link'],
                    required_skills=j['required_skills'],
                    required_experience=j['required_experience'],
                    email=j.get('email'), # <--- This comes from our Google search
                    status="found"
                )
                db.add(new_job)
        db.commit()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()
        
@app.post("/search-jobs")
async def search_jobs(email: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.skills:
        raise HTTPException(status_code=400, detail="Please upload resume first")

    # Start the scraper in the background
    background_tasks.add_task(run_scraping_logic, user.id, user.skills, user.experience)
    return {"message": "Job search started"}

@app.get("/get-jobs")
def get_jobs(email: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    jobs = db.query(Job).filter(Job.user_id == user.id).all()
    return jobs

# Inside backend/main.py

@app.post("/apply-to-job/{job_id}")
async def apply_to_job(job_id: int, custom_email: str = None, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    user = db.query(User).filter(User.id == job.user_id).first()
    
    if not job or not user:
        raise HTTPException(status_code=404, detail="Data not found")

    # LOGIC: Use custom_email if user edited it, else use job.email (constant mail id)
    final_recipient = custom_email if custom_email and "@" in custom_email else job.email
    
    if not final_recipient:
        raise HTTPException(status_code=400, detail="Recipient email is missing")

    # 1. Generate Matching Content with Ollama
    email_data = mail_service.generate_personalized_email(
        user_name=user.email.split('@')[0],
        user_skills=user.skills,
        user_exp=user.experience,
        job_title=job.title,
        company=job.company,
        job_link=job.link
    )

    # 2. Send the Mail
    success = mail_service.send_email(
        recipient_email=final_recipient,
        subject=email_data['subject'],
        body=email_data['body']
    )
    
    if success:
        job.status = "applied"
        job.date_applied = datetime.now()
        db.commit()
        return {"status": "success", "sent_to": final_recipient}
    else:
        raise HTTPException(status_code=500, detail="SMTP failed to send")
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)