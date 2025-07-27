# resume_screener_service/database/db_manager.py

import sqlite3
import json
import os

DB_FILE = os.path.join(os.path.dirname(__file__), 'resume_screener.db')

def create_connection():
    """Create a database connection to the SQLite database."""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
    return conn

def create_tables():
    """Create tables if they don't exist."""
    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS resumes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    name TEXT,
                    email TEXT,
                    phone TEXT,
                    skills TEXT, -- Stored as JSON string
                    experience TEXT, -- Stored as JSON string
                    education TEXT, -- Stored as JSON string
                    raw_text TEXT,
                    upload_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS screening_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    resume_id INTEGER NOT NULL,
                    job_description_id TEXT, -- Can be an ID from friend's service or direct JD text hash
                    job_description_text TEXT NOT NULL,
                    ai_score REAL NOT NULL,
                    ai_reasoning TEXT,
                    human_feedback_score REAL, -- For iterative learning
                    human_feedback_comment TEXT,
                    screening_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (resume_id) REFERENCES resumes (id)
                )
            """)
            conn.commit()
            print("Database tables created/checked.")
        except sqlite3.Error as e:
            print(f"Error creating tables: {e}")
        finally:
            conn.close()

def insert_resume(filename, parsed_data):
    """Inserts a parsed resume into the database."""
    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO resumes (filename, name, email, phone, skills, experience, education, raw_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                filename,
                parsed_data.get('name'),
                parsed_data.get('email'),
                parsed_data.get('phone'),
                json.dumps(parsed_data.get('skills', [])),
                json.dumps(parsed_data.get('experience', [])),
                json.dumps(parsed_data.get('education', [])),
                parsed_data.get('raw_text')
            ))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error inserting resume: {e}")
        finally:
            conn.close()
    return None

def insert_screening_result(resume_id, job_description_text, ai_score, ai_reasoning, job_description_id=None):
    """Inserts a screening result into the database."""
    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO screening_results (resume_id, job_description_id, job_description_text, ai_score, ai_reasoning)
                VALUES (?, ?, ?, ?, ?)
            """, (resume_id, job_description_id, job_description_text, ai_score, ai_reasoning))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error inserting screening result: {e}")
        finally:
            conn.close()
    return None

def get_resume_by_id(resume_id):
    """Fetches a resume by its ID."""
    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM resumes WHERE id = ?", (resume_id,))
            row = cursor.fetchone()
            if row:
                # Convert JSON strings back to lists/dicts
                cols = [description[0] for description in cursor.description]
                resume_dict = dict(zip(cols, row))
                if 'skills' in resume_dict and resume_dict['skills']:
                    resume_dict['skills'] = json.loads(resume_dict['skills'])
                if 'experience' in resume_dict and resume_dict['experience']:
                    resume_dict['experience'] = json.loads(resume_dict['experience'])
                if 'education' in resume_dict and resume_dict['education']:
                    resume_dict['education'] = json.loads(resume_dict['education'])
                return resume_dict
        except sqlite3.Error as e:
            print(f"Error fetching resume: {e}")
        finally:
            conn.close()
    return None

def update_screening_feedback(result_id, human_score, human_comment):
    """Updates a screening result with human feedback."""
    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE screening_results
                SET human_feedback_score = ?, human_feedback_comment = ?
                WHERE id = ?
            """, (human_score, human_comment, result_id))
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error updating feedback: {e}")
        finally:
            conn.close()
    return False

if __name__ == '__main__':
    create_tables()

    # Example Usage:
    # parsed_sample_resume = {
    #     "name": "Test User",
    #     "email": "test@example.com",
    #     "phone": "1234567890",
    #     "skills": ["Python", "Flask"],
    #     "experience": ["2 years"],
    #     "education": ["B.Sc. CS"],
    #     "raw_text": "Sample resume text for Test User."
    # }
    #
    # resume_id = insert_resume("test_user_resume.pdf", parsed_sample_resume)
    # if resume_id:
    #     print(f"Inserted resume with ID: {resume_id}")
    #     job_desc = "Seeking a Python developer with 2+ years of experience."
    #     ai_score = 85.5
    #     ai_reason = "Matched Python skill and experience."
    #     result_id = insert_screening_result(resume_id, job_desc, ai_score, ai_reason)
    #     if result_id:
    #         print(f"Inserted screening result with ID: {result_id}")
    #         # Simulate human feedback
    #         update_screening_feedback(result_id, 90.0, "Very strong candidate, good fit.")
    #         print("Updated feedback.")
    #
    # fetched_resume = get_resume_by_id(resume_id)
    # if fetched_resume:
    #     print("\nFetched Resume:")
    #     print(json.dumps(fetched_resume, indent=4))