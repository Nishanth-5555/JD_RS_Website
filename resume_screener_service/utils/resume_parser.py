# resume_screener_service/utils/resume_parser.py (continued from above)

import spacy
import re
import os

# Load SpaCy model once globally to avoid reloading for each request
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("SpaCy model 'en_core_web_sm' not found. Downloading...")
    spacy.cli.download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

# Load common skills from file
def load_common_skills(file_path):
    skills = set()
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                skills.add(line.strip().lower())
    except FileNotFoundError:
        print(f"Skills file not found: {file_path}. Please create it.")
    return list(skills)

COMMON_SKILLS_FILE = os.path.join(os.path.dirname(__file__), '../data/common_skills.txt')
KNOWN_SKILLS = load_common_skills(COMMON_SKILLS_FILE)
# Sort by length descending to match longer phrases first (e.g., "Machine Learning" before "Learning")
KNOWN_SKILLS.sort(key=len, reverse=True)


def parse_resume_info(resume_text: str) -> dict:
    """
    Parses a resume's text to extract key information.
    This is a rule-based approach and may require fine-tuning.
    """
    doc = nlp(resume_text)
    extracted_data = {
        "name": None,
        "email": None,
        "phone": None,
        "skills": [],
        "experience": [],
        "education": [],
        "raw_text": resume_text # Store raw text for later use if needed
    }

    # --- 1. Extract Name (Heuristic) ---
    # Often, the name is the first non-email/phone entity, or the first prominent PERSON entity
    # This is highly heuristic and can fail. A more robust solution might involve training a custom NER.
    name_candidates = []
    for ent in doc.ents:
        if ent.label_ == "PERSON" and len(ent.text.split()) >= 2: # At least two words for a name
            name_candidates.append(ent.text)
            break # Take the first person found

    if name_candidates:
        extracted_data['name'] = name_candidates[0]
    else: # Fallback: Try to guess from the first non-empty line
        lines = [line.strip() for line in resume_text.split('\n') if line.strip()]
        if lines:
            # Simple heuristic: often the first or second line is the name
            # Avoid lines that look like emails, phones, or common job titles
            for line in lines[:3]: # Check first few lines
                if '@' not in line and not re.search(r'\d{10}', line) and len(line.split()) < 5:
                    extracted_data['name'] = line
                    break


    # --- 2. Extract Email & Phone ---
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    phone_pattern = r'(?:\+?(\d{1,3}))?[-. (]*(\d{3})[-. )]*(\d{3})[-. ]*(\d{4})(?: *x(\d+))?' # More generic
    
    emails = re.findall(email_pattern, resume_text)
    if emails:
        extracted_data['email'] = emails[0]

    phones = re.findall(phone_pattern, resume_text)
    if phones:
        # Reconstruct phone number to a clean format
        extracted_data['phone'] = ''.join(phones[0] if isinstance(phones[0], tuple) else phones[0])


    # --- 3. Extract Skills ---
    # Using a predefined list and checking for presence, prioritize longer matches
    found_skills = set()
    text_lower = resume_text.lower()
    for skill in KNOWN_SKILLS:
        if skill.lower() in text_lower:
            found_skills.add(skill)
    extracted_data['skills'] = list(found_skills)

    # --- 4. Extract Experience (Basic heuristic) ---
    # Look for keywords and try to extract sections around them
    experience_keywords = ["experience", "work history", "employment", "professional background"]
    experience_section = ""
    for keyword in experience_keywords:
        if keyword in text_lower:
            # Try to find the section by looking for common headings
            match = re.search(r'(?:' + keyword + r')\s*(.*?)(\n\n|$)', text_lower, re.IGNORECASE | re.DOTALL)
            if match:
                experience_section = match.group(0) # Get the matched section including keyword
                break
    
    # Refine experience section extraction
    # This is notoriously hard without custom NER or more advanced parsing
    # For now, we'll just capture general "experience years" if found
    years_experience_match = re.search(r'(\d+)\s*(?:years|yrs?)\s+(?:of)?\s*(?:experience|exp|background)', text_lower, re.IGNORECASE)
    if years_experience_match:
        extracted_data['experience'].append(f"{years_experience_match.group(1)} years experience")
    
    # You could also extract company names and titles if patterns are consistent
    # Example: "Software Engineer at Google (2020-Present)"
    # This requires more complex regex/SpaCy rule-based matching.
    # For a basic MVP, years of experience or just keywords might suffice.
    
    # --- 5. Extract Education (Basic heuristic) ---
    education_keywords = ["education", "academic background", "qualifications"]
    for keyword in education_keywords:
        if keyword in text_lower:
            match = re.search(r'(?:' + keyword + r')\s*(.*?)(\n\n|$)', text_lower, re.IGNORECASE | re.DOTALL)
            if match:
                education_section_text = match.group(0)
                # Now try to extract degree, university, year from this section
                # Example patterns: "B.Tech in CS from XYZ University (2020)"
                degree_pattern = r'(?:b\.?\s?s|m\.?\s?s|b\.?\s?a|ph\.?\s?d|bachelor|master|doctor|eng\.)[^.\n]*?(?:in|of)\s+([a-zA-Z\s]+)'
                university_pattern = r'(?:university|institute|college|school)\s+of\s+([a-zA-Z\s]+)|([a-zA-Z\s]+(?:university|institute|college))'
                year_pattern = r'\b(?:19|20)\d{2}\b' # Basic year
                
                degrees = re.findall(degree_pattern, education_section_text, re.IGNORECASE)
                universities = re.findall(university_pattern, education_section_text, re.IGNORECASE)
                years = re.findall(year_pattern, education_section_text)

                if degrees:
                    # Clean up degree match, take first group
                    deg = degrees[0] if isinstance(degrees[0], str) else (degrees[0][0] or degrees[0][1])
                    extracted_data['education'].append(f"Degree: {deg.strip()}")
                if universities:
                    # Clean up university match, take first non-empty group
                    uni = universities[0] if isinstance(universities[0], str) else (universities[0][0] or universities[0][1])
                    extracted_data['education'].append(f"University: {uni.strip()}")
                if years:
                    extracted_data['education'].append(f"Year: {years[0]}")
                break

    return extracted_data

if __name__ == '__main__':
    # Test the full parsing
    dummy_resume_path = '../data/dummy_resume.txt'
    if not os.path.exists(dummy_resume_path):
         with open(dummy_resume_path, 'w') as f:
            f.write("John Doe\nSoftware Engineer\njohn.doe@example.com\n+919876543210\n\nSummary: Highly motivated software engineer with 5 years of experience in developing scalable web applications.\n\nSkills:\nPython, Java, SQL, AWS, Docker, Kubernetes, Machine Learning, Data Structures, Algorithms, Communication, Leadership\n\nExperience:\nSenior Software Engineer\nTech Solutions Pvt. Ltd., Bengaluru\nJan 2020 - Present\n- Led development of microservices using Python and Flask.\n- Implemented ML models for fraud detection, reducing incidents by 15%.\n- Mentored junior developers and conducted code reviews.\n\nSoftware Developer\nInnovate Corp., Chennai\nAug 2018 - Dec 2019\n- Developed RESTful APIs using Java and Spring Boot.\n- Contributed to database design and optimization (SQL).\n\nEducation:\nB.Tech in Computer Science\nXYZ University, Bengaluru\n2014 - 2018\nGPA: 9.0/10.0\n")

    resume_text = extract_text_from_file(dummy_resume_path)
    if resume_text:
        parsed_info = parse_resume_info(resume_text)
        import json
        print("\n--- Parsed Resume Info ---")
        print(json.dumps(parsed_info, indent=4))