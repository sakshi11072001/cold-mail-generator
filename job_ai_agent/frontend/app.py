import streamlit as st
import requests

# Page Configuration
st.set_page_config(page_title="AI Job Assistant", page_icon="🚀", layout="wide")

# The URL where your FastAPI backend is running
API_URL = "http://127.0.0.1:8080"

def main():
    st.title("🚀 AI Job Application Assistant")

    # Initialize session state for login tracking
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user_email = ""

    if not st.session_state.logged_in:
        auth_page()
    else:
        dashboard()

def auth_page():
    """Handles Login and Sign Up UI"""
    st.info("Welcome! Please log in to manage your job applications.")
    tabs = st.tabs(["Login", "Sign Up"])
    
    with tabs[0]:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pw")
        if st.button("Login", use_container_width=True):
            handle_auth("login", email, password)

    with tabs[1]:
        s_email = st.text_input("Email", key="signup_email")
        s_password = st.text_input("Password", type="password", key="signup_pw")
        if st.button("Create Account", use_container_width=True):
            handle_auth("signup", s_email, s_password)

def handle_auth(endpoint, email, password):
    """Communicates with the Backend for Authentication"""
    if not email or not password:
        st.warning("Please fill in all fields.")
        return
    try:
        response = requests.post(f"{API_URL}/{endpoint}", json={"email": email, "password": password})
        if response.status_code == 200:
            if endpoint == "login":
                st.session_state.logged_in = True
                st.session_state.user_email = email
                st.rerun()
            else:
                st.success("Account created! Please switch to Login tab.")
        else:
            st.error(response.json().get("detail", "Authentication failed."))
    except Exception as e:
        st.error(f"Backend connection error: {e}")

def dashboard():
    """Main Application Dashboard"""
    # Sidebar Navigation
    st.sidebar.title("👤 My Profile")
    st.sidebar.write(f"Logged in as: **{st.session_state.user_email}**")
    
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

    st.sidebar.divider()
    st.sidebar.subheader("Automations")
    if st.sidebar.button("⏰ Process 2-Day Reminders", use_container_width=True):
        with st.spinner("Processing follow-ups..."):
            res = requests.post(f"{API_URL}/process-reminders")
            if res.status_code == 200:
                st.sidebar.success(res.json()['message'])

    # --- SECTION 1: RESUME UPLOAD ---
    st.header("1. Upload & Analyze Resume")
    uploaded_file = st.file_uploader("Upload your PDF Resume", type=["pdf"])
    
    if uploaded_file:
        if st.button("📄 Parse Resume with Ollama"):
            with st.spinner("Analyzing your skills and experience..."):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                params = {"email": st.session_state.user_email}
                try:
                    res = requests.post(f"{API_URL}/upload-resume", params=params, files=files)
                    if res.status_code == 200:
                        data = res.json()
                        st.success("Resume Parsed Successfully!")
                        c1, c2 = st.columns(2)
                        c1.metric("Skills Found", len(data.get('skills', [])))
                        c2.metric("Total Experience", f"{data.get('experience', 0)} Years")
                        st.write(f"**Keywords Extracted:** {', '.join(data.get('skills', []))}")
                    else:
                        st.error("Failed to parse resume.")
                except Exception as e:
                    st.error(f"Connection error: {e}")

    st.divider()

    # --- SECTION 2: JOB SEARCH ---
    st.header("2. Match Jobs")
    st.write("Find current openings on LinkedIn & ZipRecruiter matching your profile.")
    
    col_a, col_b = st.columns([1, 4])
    with col_a:
        if st.button("🔍 Find Jobs Now", type="primary", use_container_width=True):
            with st.spinner("Scraping portal results..."):
                try:
                    requests.post(f"{API_URL}/search-jobs", params={"email": st.session_state.user_email})
                    st.toast("Search started in background! Wait 5 seconds.")
                except:
                    st.error("Could not start search.")

    with col_b:
        if st.button("🔄 Refresh Matches", use_container_width=True):
            st.rerun()

    # --- SECTION 3: DISPLAY RESULTS & APPLY ---
    st.subheader("Matching Job Openings")
    try:
        jobs_resp = requests.get(f"{API_URL}/get-jobs", params={"email": st.session_state.user_email})
        if jobs_resp.status_code == 200:
            jobs = jobs_resp.json()
            if not jobs:
                st.info("No jobs found yet. Click 'Find Jobs Now' to start the hunt.")
            else:
                for job in jobs:
                    # Professional container for each job card
                    with st.container(border=True):
                        st.subheader(f"{job['title']}")
                        st.write(f"🏢 **{job['company']}**")
                        
                        # Skill and Exp Display
                        col_info1, col_info2 = st.columns(2)
                        col_info1.write(f"🛠 **Required:** {job.get('required_skills', 'N/A')}")
                        col_info2.write(f"⏳ **Target Exp:** {job.get('required_experience', 'N/A')}")

                        # Editable Recruiter Email (Default is the generated constant mail id)
                        edited_email = st.text_input(
                            "Recruiter Email (Verify or Edit):", 
                            value=job.get('email', ''), 
                            key=f"input_{job['id']}"
                        )
                        
                        st.write(f"📊 **Status:** `{job['status'].upper()}`")
                        
                        btn_col1, btn_col2 = st.columns([1, 1])
                        
                        with btn_col1:
                            if job['status'] == "found":
                                if st.button("📧 Apply with AI Match", key=f"apply_{job['id']}", type="primary", use_container_width=True):
                                    with st.spinner("Ollama is drafting email..."):
                                        # Pass the edited email to the backend
                                        apply_res = requests.post(
                                            f"{API_URL}/apply-to-job/{job['id']}", 
                                            params={"custom_email": edited_email}
                                        )
                                        if apply_res.status_code == 200:
                                            st.success("Application Sent!")
                                            st.rerun()
                                        else:
                                            st.error("Failed to send email.")
                            else:
                                st.button("✅ Application Sent", disabled=True, use_container_width=True, key=f"disabled_{job['id']}")
                        
                        with btn_col2:
                            st.link_button("🌐 View Portal Listing", job['link'], use_container_width=True)
        else:
            st.error("Could not fetch jobs from database.")
    except Exception as e:
        st.error(f"Error loading dashboard: {e}")

if __name__ == "__main__":
    main()