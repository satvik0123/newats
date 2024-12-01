import streamlit as st
import PyPDF2
import nltk
import pandas as pd
from collections import Counter
from docx import Document
import difflib
from dotenv import load_dotenv
import os
import google.generativeai as genai
from fpdf import FPDF
import hashlib

# Download NLTK resources
nltk.download('punkt')
nltk.download('stopwords')
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

# Configure Google Generative AI (replace with your actual API key)
GOOGLE_API_KEY = "AIzaSyD95tDMjfi-0z8Kejnt8WzwOXzMQP0_RNI"
genai.configure(api_key=GOOGLE_API_KEY)

# User Credentials (in a real-world scenario, use a secure database)
USER_CREDENTIALS = {
    'student': hashlib.sha256('student123'.encode()).hexdigest(),
    'recruiter': hashlib.sha256('recruiter123'.encode()).hexdigest()
}

def verify_login(username, password):
    """Verify user credentials."""
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    return USER_CREDENTIALS.get(username) == hashed_password

def get_gemini_response(resume_text, job_desc_text, prompt):
    """Fetches a response from Gemini API."""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        input_text = f"Resume:\n{resume_text}\n\nJob Description:\n{job_desc_text}\n\nPrompt:\n{prompt}"
        
        response = model.generate_content(input_text)
        return response.text
    except Exception as e:
        st.error(f"Error in Gemini API: {e}")
        return None

def extract_text_from_pdf(pdf_file):
    """Extract text from PDF file."""
    reader = PyPDF2.PdfReader(pdf_file)
    text = ''.join([page.extract_text() for page in reader.pages])
    return text

def generate_job_match_score(job_description: str, resume_text: str) -> float:
    """Generate job match score using Gemini model."""
    try:
        model = genai.GenerativeModel('gemini-pro')

        prompt = f"""Analyze the following job description and resume,
        and provide a numerical score (0-100) representing how well
        the resume matches the job requirements. Consider:
        1. Relevant skills
        2. Professional experience
        3. Alignment with job responsibilities
        4. Keyword match

        Job Description:
        {job_description}

        Resume:
        {resume_text}

        Return only the numerical score between 0 and 100.
        """

        response = model.generate_content(prompt)

        try:
            score = float(response.text.strip())
        except ValueError:
            score = 50  # Default mid-range score

        return max(0, min(score, 100))  # Ensure score is between 0-100

    except Exception as e:
        st.error(f"Error generating score: {e}")
        return 50  # Default score on error

def login_page():
    """Login page for the ATS system."""
    st.title("GLA University ATS System - Login")
    
    # Ensure session state for login
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    role = st.selectbox("Select Role", ["Select Role", "Student", "Recruiter"])

    if st.button("Login"):
        if role == "Select Role":
            st.warning("Please select a role.")
        elif verify_login(username.lower(), password):
            st.session_state['logged_in'] = True
            st.session_state['role'] = role.lower()
            st.experimental_rerun()
        else:
            st.error("Invalid credentials. Please try again.")

def student_dashboard():
    """Dashboard for students to generate and analyze resumes."""
    st.title("**GLA University ATS System - Student Portal**")
    st.subheader("About")
    st.write("Create and analyze your resume with advanced AI-powered tools.")

    # Resume Generation Section
    st.header("Resume Generator")
    name = st.text_input("Name")
    email = st.text_input("Email")
    phone = st.text_input("Phone Number")
    skills = st.text_area("Skills")
    education = st.text_area("Education")
    work_experience = st.text_area("Work Experience")
    projects = st.text_area("Projects")
    achievements = st.text_area("Achievements")
    certifications = st.text_area("Certifications")
    hobbies = st.text_area("Hobbies")
    
    # Job Description Upload
    st.header("Job Description Analysis")
    job_desc_file = st.file_uploader("Upload Job Description (PDF)", type="pdf")
    
    if job_desc_file and st.button("Generate Resume & Analyze"):
        # Resume Generation Logic (existing code)
        job_desc_text = extract_text_from_pdf(job_desc_file)
        
        # Analyze Resume Matching
        prompts = {
            "Match Percentage": """You are an ATS scanner. Evaluate the resume against the job description 
            and provide a match percentage. Return only a numerical value.""",
            "Relevant Skills": """Identify skills in the resume that match the job description.""",
            "Recommended Skills": """List skills from the job description not present in the resume."""
        }
        
        st.header("Resume Analysis Results")
        
        # Placeholder for resume text (in a real scenario, convert generated resume to text)
        resume_text = f"{name}\n{email}\n{phone}\n\nSkills:\n{skills}\n\nEducation:\n{education}"
        
        for title, prompt in prompts.items():
            response = get_gemini_response(resume_text, job_desc_text, prompt)
            st.subheader(title)
            st.write(response)

def recruiter_dashboard():
    """Dashboard for recruiters to rank and analyze resumes."""
    st.title("📄 Resume Ranking Application")

    # Job Description PDF Upload
    st.header("1. Upload Job Description PDF")
    job_description_pdf = st.file_uploader("Choose job description PDF", type=['pdf'])

    job_description = ""
    if job_description_pdf:
        job_description = extract_text_from_pdf(job_description_pdf)
        st.text_area("Extracted Job Description", value=job_description, height=200)

    # Resume PDF Upload
    st.header("2. Upload Resume PDFs")
    uploaded_resumes = st.file_uploader("Choose resume PDF files",
                                        type=['pdf'],
                                        accept_multiple_files=True)

    top_n = st.number_input("Number of Top Resumes", min_value=1, max_value=10, value=3)

    if st.button("Rank Resumes") and job_description and uploaded_resumes:
        with st.spinner('Analyzing Resumes...'):
            # Process resumes
            resume_data = []
            for resume_file in uploaded_resumes:
                resume_text = extract_text_from_pdf(resume_file)
                score = generate_job_match_score(job_description, resume_text)

                resume_data.append({
                    'Filename': resume_file.name,
                    'Match Score': score
                })

            # Create DataFrame and sort
            df = pd.DataFrame(resume_data)
            df_sorted = df.sort_values('Match Score', ascending=False)

            # Display results
            st.header("3. Resume Ranking Results")
            st.dataframe(df_sorted, use_container_width=True)

            # Highlight top candidates
            top_candidates = df_sorted.head(top_n)
            st.subheader("Top Candidates")
            for _, row in top_candidates.iterrows():
                st.metric(label=row['Filename'], value=f"{row['Match Score']:.2f}%")

def main():
    """Main application entry point."""
    # Initialize session state if not exists
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    # Set page configuration
    st.set_page_config(page_title="GLA ATS System", page_icon=":guardsman:")

    # Login Page or Dashboard based on login status
    if not st.session_state['logged_in']:
        login_page()
    else:
        # Add logout button
        if st.sidebar.button("Logout"):
            st.session_state['logged_in'] = False
            st.experimental_rerun()

        # Route to appropriate dashboard based on role
        if st.session_state['role'] == 'student':
            student_dashboard()
        elif st.session_state['role'] == 'recruiter':
            recruiter_dashboard()

if __name__ == "__main__":
    main()
