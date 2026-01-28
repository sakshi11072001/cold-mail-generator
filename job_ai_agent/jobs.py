import os
import requests
import warnings
import sys
from urllib3.exceptions import InsecureRequestWarning
from functools import partial

# --- RE-APPLY THE "FORCE" SSL BYPASS ---
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['PYTHONHTTPSVERIFY'] = '0'
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
requests.Session.request = partial(requests.Session.request, verify=False)

from jobspy import scrape_jobs
import pandas as pd

def search_jobs():
    print("Starting Job Search...")
    
    try:
        # We use INDEED and ZIP_RECRUITER because LinkedIn causes the 'NoneType' error
        jobs = scrape_jobs(
            site_name=["LinkedIn", "zip_recruiter"], 
            search_term="AI Engineer",
            location="India",
            results_wanted=5,
            country_indeed='India',
            # Adding a delay helps avoid being blocked
            hours_old=72 
        )

        if jobs is not None and not jobs.empty:
            print(f"\n✅ Success! Found {len(jobs)} jobs.")
            # Select only the columns we want to see
            view_columns = ['site', 'title', 'company', 'location']
            print(jobs[view_columns].head())
            
            # Save to CSV
            jobs.to_csv("scraped_jobs.csv", index=False)
            print("\nResults saved to 'scraped_jobs.csv'")
        else:
            print("\n❌ No jobs found. The websites might be blocking your network.")

    except Exception as e:
        print(f"\n❌ A library error occurred: {e}")
        print("Tip: This often happens if the website structure changed or your IP is flagged.")

if __name__ == "__main__":
    search_jobs()