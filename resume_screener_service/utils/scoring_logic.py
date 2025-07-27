# resume_screener_service/utils/scoring_logic.py

from sentence_transformers import SentenceTransformer, util
import spacy
import re
from typing import List, Dict

# Load SpaCy model for processing job descriptions (if not already loaded globally)
try:
    nlp_score = spacy.load("en_core_web_sm")
except OSError:
    print("SpaCy model 'en_core_web_sm' not found. Downloading...")
    spacy.cli.download("en_core_web_sm")
    nlp_score = spacy.load("en_core_web_sm")


# Load SentenceTransformer model once globally for efficiency
# 'all-MiniLM-L6-v2' is good balance of speed and accuracy for semantic similarity
# 'all-mpnet-base-v2' is slightly better but larger
model_sbert = SentenceTransformer('all-MiniLM-L6-v2')

def _extract_jd_requirements(jd_text: str) -> Dict[str, List[str]]:
    """
    Helper function to extract key requirements from a job description.
    This uses simple regex and keyword matching and will need refinement
    based on the typical structure of JDs from the JD Builder.
    """
    requirements = {
        "skills": [],
        "responsibilities": [],
        "experience_years": 0,
        "education": []
    }
    
    jd_lower = jd_text.lower()

    # Extract skills (simple keyword matching, can be improved with NER)
    # This assumes skills are often listed explicitly.
    # For a robust solution, you'd match against your KNOWN_SKILLS list.
    skills_match = re.search(r'(?:(?:required|key)\s+skills|skills|technical\s+qualifications):?\s*(.*?)(?:\n\n|\n[A-Z][a-zA-Z\s]+:|\Z)', jd_lower, re.IGNORECASE | re.DOTALL)
    if skills_match:
        skills_text = skills_match.group(1).replace('*', '').replace('-', '').replace('•', '').strip()
        requirements['skills'] = [s.strip() for s in re.split(r'[,;\n]', skills_text) if s.strip()]
    
    # Extract responsibilities
    responsibilities_match = re.search(r'(?:key\s+responsibilities|responsibilities|duties):?\s*(.*?)(?:\n\n|\n[A-Z][a-zA-Z\s]+:|\Z)', jd_lower, re.IGNORECASE | re.DOTALL)
    if responsibilities_match:
        responsibilities_text = responsibilities_match.group(1).replace('*', '').replace('-', '').replace('•', '').strip()
        requirements['responsibilities'] = [r.strip() for r in re.split(r'[,;\n]', responsibilities_text) if r.strip()]

    # Extract experience years
    exp_match = re.search(r'(\d+)\s*(?:\+|plus)?\s*(?:years|yrs?)\s+(?:of\s+)?(?:experience|exp)', jd_lower, re.IGNORECASE)
    if exp_match:
        requirements['experience_years'] = int(exp_match.group(1))
    
    # Extract education
    edu_match = re.search(r'(?:education|qualifications|academic\s+background):?\s*(.*?)(?:\n\n|\n[A-Z][a-zA-Z\s]+:|\Z)', jd_lower, re.IGNORECASE | re.DOTALL)
    if edu_match:
        edu_text = edu_match.group(1).replace('*', '').replace('-', '').replace('•', '').strip()
        requirements['education'] = [e.strip() for e in re.split(r'[,;\n]', edu_text) if e.strip()]

    return requirements

def score_resume(parsed_resume_data: Dict, job_description_text: str, sbert_model: SentenceTransformer) -> (float, str):
    """
    Scores a parsed resume against a job description.
    Returns a score (0-100) and a brief reasoning string.
    """
    resume_skills = parsed_resume_data.get('skills', [])
    resume_experience_text = " ".join(parsed_resume_data.get('experience', []))
    resume_education_text = " ".join(parsed_resume_data.get('education', []))
    resume_name = parsed_resume_data.get('name', 'Candidate')
    
    jd_requirements = _extract_jd_requirements(job_description_text)
    jd_required_skills = jd_requirements.get('skills', [])
    jd_responsibilities = jd_requirements.get('responsibilities', [])
    jd_min_experience_years = jd_requirements.get('experience_years', 0)
    jd_required_education = jd_requirements.get('education', [])

    total_score = 0
    reasoning_parts = []

    # --- 1. Skill Matching (Highest Weight) ---
    skill_match_score = 0
    if jd_required_skills:
        # Generate embeddings for JD skills and resume skills
        jd_skill_embeddings = sbert_model.encode(jd_required_skills, convert_to_tensor=True)
        resume_skill_embeddings = sbert_model.encode(resume_skills, convert_to_tensor=True)

        if len(resume_skill_embeddings) > 0:
            # Calculate similarity matrix between JD skills and resume skills
            cosine_scores = util.cos_sim(jd_skill_embeddings, resume_skill_embeddings)
            
            # For each required JD skill, find its best match in resume skills
            matched_jd_skills = 0
            for i in range(len(jd_required_skills)):
                if len(cosine_scores) > 0 and len(cosine_scores[i]) > 0:
                    max_sim = cosine_scores[i].max().item()
                    if max_sim > 0.6: # Threshold for a "match"
                        matched_jd_skills += 1
            
            skill_match_score = (matched_jd_skills / len(jd_required_skills)) * 100
            reasoning_parts.append(f"Matched {matched_jd_skills}/{len(jd_required_skills)} key skills ({int(skill_match_score)}%).")
        else:
            reasoning_parts.append("No skills found in resume to match against JD skills.")
            skill_match_score = 0
    else:
        reasoning_parts.append("No specific skills required in JD.")
        skill_match_score = 100 # No skills required, so full score for this part

    total_score += skill_match_score * 0.40 # 40% weight for skills

    # --- 2. Experience Years Matching ---
    experience_years_in_resume = 0
    if parsed_resume_data.get('experience'):
        # Try to extract years from the parsed experience text
        exp_match = re.search(r'(\d+)\s+years', resume_experience_text, re.IGNORECASE)
        if exp_match:
            experience_years_in_resume = int(exp_match.group(1))

    experience_score = 0
    if jd_min_experience_years > 0:
        if experience_years_in_resume >= jd_min_experience_years:
            experience_score = 100
            reasoning_parts.append(f"Meets/Exceeds {jd_min_experience_years} years experience ({experience_years_in_resume} years found).")
        else:
            experience_score = (experience_years_in_resume / jd_min_experience_years) * 100 if jd_min_experience_years > 0 else 0
            reasoning_parts.append(f"Has {experience_years_in_resume} years experience (requires {jd_min_experience_years}).")
    else:
        experience_score = 100 # No minimum experience required
        reasoning_parts.append("No minimum experience required in JD.")
    
    total_score += experience_score * 0.30 # 30% weight for experience years

    # --- 3. Responsibility/Summary Semantic Match ---
    responsibility_score = 0
    if jd_responsibilities and parsed_resume_data.get('raw_text'):
        jd_resp_text = " ".join(jd_responsibilities)
        resume_summary_or_raw = parsed_resume_data.get('raw_text') # Use raw text for broader context
        
        jd_resp_embedding = sbert_model.encode(jd_resp_text, convert_to_tensor=True)
        resume_overall_embedding = sbert_model.encode(resume_summary_or_raw, convert_to_tensor=True)
        
        sim = util.cos_sim(jd_resp_embedding, resume_overall_embedding).item()
        responsibility_score = sim * 100
        reasoning_parts.append(f"Overall resume content aligns with responsibilities ({int(responsibility_score)}%).")
    else:
        reasoning_parts.append("Cannot assess responsibilities due to missing JD or resume content.")
        responsibility_score = 50 # Neutral if no data to compare

    total_score += responsibility_score * 0.20 # 20% weight for responsibility alignment

    # --- 4. Education Matching ---
    education_score = 0
    if jd_required_education:
        matched_edu = 0
        for req_edu in jd_required_education:
            if req_edu.lower() in resume_education_text.lower():
                matched_edu = 1 # Simple match if any required education is mentioned
                break
        education_score = matched_edu * 100
        reasoning_parts.append(f"Education matches JD requirements ({int(education_score)}%).")
    else:
        education_score = 100 # No specific education required
        reasoning_parts.append("No specific education required in JD.")

    total_score += education_score * 0.10 # 10% weight for education

    final_score = round(total_score, 2)
    overall_reasoning = " ".join(reasoning_parts)
    
    return final_score, overall_reasoning

if __name__ == '__main__':
    # For testing scoring_logic.py module
    from resume_parser import parse_resume_info, extract_text_from_file
    import os

    # Create dummy JD for testing
    dummy_jd = """
    Job Summary: Seeking a talented Senior Software Engineer with a passion for building scalable solutions.

    Key Responsibilities:
    - Design and implement microservices using Python.
    - Develop and deploy Machine Learning models.
    - Collaborate with product and design teams.
    - Mentor junior engineers.

    Required Qualifications:
    - Bachelor's degree in Computer Science or related field.
    - 5+ years of experience in software development.
    - Strong skills in Python, AWS, SQL, Machine Learning.

    What We Offer:
    - Competitive salary and benefits.
    - Flexible work environment.
    """

    # Ensure dummy_resume.txt from section 3 is created
    dummy_resume_path = '../data/dummy_resume.txt'
    if not os.path.exists(dummy_resume_path):
         with open(dummy_resume_path, 'w') as f:
            f.write("John Doe\nSoftware Engineer\njohn.doe@example.com\n+919876543210\n\nSummary: Highly motivated software engineer with 5 years of experience in developing scalable web applications.\n\nSkills:\nPython, Java, SQL, AWS, Docker, Kubernetes, Machine Learning, Data Structures, Algorithms, Communication, Leadership\n\nExperience:\nSenior Software Engineer\nTech Solutions Pvt. Ltd., Bengaluru\nJan 2020 - Present\n- Led development of microservices using Python and Flask.\n- Implemented ML models for fraud detection, reducing incidents by 15%.\n- Mentored junior developers and conducted code reviews.\n\nSoftware Developer\nInnovate Corp., Chennai\nAug 2018 - Dec 2019\n- Developed RESTful APIs using Java and Spring Boot.\n- Contributed to database design and optimization (SQL).\n\nEducation:\nB.Tech in Computer Science\nXYZ University, Bengaluru\n2014 - 2018\nGPA: 9.0/10.0\n")

    resume_text = extract_text_from_file(dummy_resume_path)
    if resume_text:
        parsed_info = parse_resume_info(resume_text)
        score, reasoning = score_resume(parsed_info, dummy_jd, model_sbert)
        print(f"\n--- Score for {parsed_info.get('name', 'N/A')} ---")
        print(f"Score: {score}%")
        print(f"Reasoning: {reasoning}")

        # Test a resume with fewer matches
        less_match_resume_path = '../data/less_match_resume.txt'
        with open(less_match_resume_path, 'w') as f:
            f.write("Jane Smith\nMarketing Specialist\njane.smith@example.com\n+918765432109\n\nSkills:\nContent Creation, SEO, Social Media Marketing, Photoshop\n\nExperience:\nMarketing Associate\nDigital Ads Co., Mumbai\nJan 2022 - Present\n- Managed social media campaigns.\n- Wrote marketing copy.\n\nEducation:\nB.A. in Mass Communication\nCity College, Mumbai\n2018 - 2022\n")
        
        less_match_text = extract_text_from_file(less_match_resume_path)
        if less_match_text:
            parsed_less_match = parse_resume_info(less_match_text)
            score_less, reason_less = score_resume(parsed_less_match, dummy_jd, model_sbert)
            print(f"\n--- Score for {parsed_less_match.get('name', 'N/A')} ---")
            print(f"Score: {score_less}%")
            print(f"Reasoning: {reason_less}")