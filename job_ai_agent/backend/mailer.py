
import smtplib
import ollama
import json
from email.message import EmailMessage

SMTP_EMAIL = "sakshiranka@gmail.com"
SMTP_PASSWORD = "qxkp wbzm jzls qexo"

class MailService:
    def generate_personalized_email(self, user_name, user_skills, user_exp, job_title, company, job_link):
        """Generates a matching email using Ollama"""
        prompt = f"""
        Write a professional job application email.
        
        Candidate Name: {user_name}
        Candidate Skills: {user_skills}
        Candidate Experience: {user_exp} years
        
        Target Role: {job_title}
        Company: {company}
        Job Reference/Link: {job_link}
        
        Task:
        1. Match the candidate's skills to the job role.
        2. Keep it concise (max 150 words).
        3. Mention that the resume is attached.
        4. Include the Job Reference/Link in the body.
        
        Return strictly JSON with 'subject' and 'body' keys.
        """
        try:
            response = ollama.generate(model="llama3.2", prompt=prompt, format="json")
            return json.loads(response['response'])
        except Exception as e:
            return {
                "subject": f"Application for {job_title} - {user_name}",
                "body": f"Hi,\n\nI am applying for the {job_title} role. I have {user_exp} years of experience and skills in {user_skills}.\n\nJob Link: {job_link}\n\nBest, {user_name}"
            }

    def send_email(self, recipient_email, subject, body):
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = SMTP_EMAIL
        msg['To'] = recipient_email
        msg.set_content(body)

        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 587) as smtp:
                smtp.login(SMTP_EMAIL, SMTP_PASSWORD)
                smtp.send_message(msg)
            return True
        except Exception as e:
            print(f"SMTP Error: {e}")
            return False

mail_service = MailService()