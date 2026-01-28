# backend/scraper.py
import re

class JobScraper:
    def generate_corporate_email(self, company_name):
        """Generates a standard HR email based on company name"""
        # 1. Clean the company name
        # Remove "Pvt Ltd", "Inc", "Solutions", "Technologies", "Corp" etc.
        clean_name = company_name.lower()
        remove_words = ["pvt", "ltd", "limited", "inc", "corp", "corporation", "solutions", "technologies", "india"]
        for word in remove_words:
            clean_name = clean_name.replace(word, "")
        
        # 2. Remove spaces and special characters
        clean_name = re.sub(r'[^a-zA-Z0-9]', '', clean_name)
        
        # 3. Create the domain and email
        # We assume .com for most or .in for Indian companies
        domain = f"{clean_name}.com"
        
        # We can pick a standard alias: hr@, careers@, or recruiter@
        return f"hr@{domain}"

    async def search_jobs(self, skills: list, experience: int):
        search_term = skills[0] if skills else "AI Engineer"
        try:
            # 1. Get Job List using JobSpy
            jobs = scrape_jobs(
                site_name=["linkedin", "zip_recruiter"], 
                search_term=search_term,
                location="India",
                results_wanted=5,
                hours_old=72 
            )
            
            if jobs is None or jobs.empty:
                return []

            final_jobs = []
            for _, row in jobs.iterrows():
                # 2. INSTANTLY generate the email
                email = self.generate_corporate_email(row['company'])
                
                final_jobs.append({
                    "title": row['title'],
                    "company": row['company'],
                    "link": row['job_url'],
                    "email": email,
                    "required_experience": f"{experience}+ years"
                })
            return final_jobs
        except Exception as e:
            print(f"Scraper error: {e}")
            return []

job_scraper = JobScraper()