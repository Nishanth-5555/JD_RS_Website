# resume_screener_service/app.py

from flask import Flask, request, jsonify
from flask_cors import CORS # Import CORS for cross-origin requests
import os
import uuid # For unique filenames
from werkzeug.utils import secure_filename # Recommended for secure filenames
import tempfile # For temporary file storage
import logging # For logging messages to console

# Configure basic logging for Flask app
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
app_logger = logging.getLogger(__name__) # Get logger for this module

# Import your utility functions
# Make sure these imports correctly point to your utils/ and database/ directories
from utils.resume_parser import extract_text_from_file, parse_resume_info
from utils.scoring_logic import score_resume, model_sbert # Import the SBERT model instance
from database.db_manager import create_tables, insert_resume, insert_screening_result

app = Flask(__name__)
app.debug = True # REMEMBER: Set to False for production!
CORS(app) # Enable CORS for all routes, important for frontend communication

# Ensure database tables are created when the app starts
app_logger.info("Checking/creating database tables...")
create_tables()
app_logger.info("Database setup complete.")

@app.route('/screen_resumes', methods=['POST'])
def screen_resumes_endpoint():
    app_logger.info("Received request to /screen_resumes")

    # 1. Validate Input: Job Description
    if 'job_description' not in request.form:
        app_logger.error("Missing 'job_description' form field in request.")
        return jsonify({"error": "Missing 'job_description' form field"}), 400
    
    job_description = request.form['job_description']
    app_logger.info(f"Job Description received. Length: {len(job_description)} chars.")

    # 2. Validate Input: Resume Files
    if 'resume_files' not in request.files:
        app_logger.error("No 'resume_files' part in the request.")
        return jsonify({"error": "No 'resume_files' part in the request"}), 400

    resume_files = request.files.getlist('resume_files')
    if not resume_files or all(f.filename == '' for f in resume_files):
        app_logger.warning("No files selected or uploaded.")
        return jsonify({"error": "No files selected or uploaded"}), 400

    app_logger.info(f"Received {len(resume_files)} resume file(s).")
    processed_candidates = []
    
    for resume_file in resume_files:
        if resume_file.filename == '':
            continue # Skip empty file fields

        original_filename = secure_filename(resume_file.filename)
        app_logger.info(f"Processing file: {original_filename}")
        
        # Use tempfile to ensure proper handling of temporary files
        temp_file_fd, temp_file_path = tempfile.mkstemp(suffix=os.path.splitext(original_filename)[1])
        os.close(temp_file_fd) # Close file descriptor immediately after creation
        resume_file.save(temp_file_path) # Save the uploaded file to the temp path
        app_logger.info(f"Saved temporary file to: {temp_file_path}")

        parsed_data = {}
        ai_score = 0.0
        ai_reasoning = "Processing failed."
        resume_db_id = None # Database ID for the resume

        try:
            # 1. Extract Text from Resume File
            app_logger.info("Extracting text from resume file...")
            raw_text = extract_text_from_file(temp_file_path)
            if not raw_text:
                raise ValueError("Could not extract text from resume. File might be empty or unreadable.")
            app_logger.info(f"Text extracted. Length: {len(raw_text)} chars.")

            # 2. Parse Information from Resume Text
            app_logger.info("Parsing information from extracted text...")
            parsed_data = parse_resume_info(raw_text)
            app_logger.info(f"Parsed data: Name={parsed_data.get('name')}, Skills={len(parsed_data.get('skills', []))} found.")
            
            # 3. Store Raw and Parsed Data in Database
            app_logger.info("Inserting resume into database...")
            resume_db_id = insert_resume(original_filename, parsed_data)
            if not resume_db_id:
                raise Exception("Failed to save resume to database.")
            app_logger.info(f"Resume saved to DB with ID: {resume_db_id}")

            # 4. Score Resume against Job Description
            app_logger.info("Scoring resume against job description...")
            # model_sbert is loaded globally in scoring_logic.py
            ai_score, ai_reasoning = score_resume(parsed_data, job_description, model_sbert)
            app_logger.info(f"Scoring complete. Score: {ai_score}, Reasoning: {ai_reasoning}")
            
            # 5. Store Screening Result in Database
            app_logger.info("Inserting screening result into database...")
            insert_screening_result(resume_db_id, job_description, ai_score, ai_reasoning)
            app_logger.info("Screening result saved to DB.")

        except ValueError as ve:
            ai_reasoning = f"File processing/parsing error: {ve}"
            app_logger.error(f"ValueError during resume processing: {ve}", exc_info=True)
        except Exception as e:
            ai_reasoning = f"Server error during processing: {str(e)}"
            app_logger.error(f"Unhandled error processing {original_filename}: {e}", exc_info=True)
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                app_logger.info(f"Cleaned up temporary file: {temp_file_path}")
            else:
                app_logger.info(f"Temporary file not found for cleanup: {temp_file_path}")

        processed_candidates.append({
            "id": resume_db_id, # ID from your database
            "filename": original_filename,
            "name": parsed_data.get("name", "N/A"),
            "score": round(ai_score, 2),
            "reasoning": ai_reasoning,
            "extracted_skills": parsed_data.get("skills", [])
            # You can add more parsed data here if needed for UI display
        })

    # Sort candidates by score (highest first)
    processed_candidates.sort(key=lambda x: x['score'], reverse=True)
    app_logger.info(f"Finished processing all resumes. Returning {len(processed_candidates)} candidates.")

    return jsonify({"status": "success", "candidates": processed_candidates})

# Global exception handler for Flask app
@app.errorhandler(Exception)
def handle_exception(e):
    app_logger.error(f"An unhandled Flask exception occurred: {e}", exc_info=True)
    response = jsonify({
        "error": "An unexpected server error occurred.",
        "details": str(e), # Provide error details only in debug mode or for internal logging
        "type": type(e).__name__
    })
    response.status_code = 500
    return response

# To run the Flask app:
if __name__ == '__main__':
    # Ensure a directory for temp uploads exists if not using system temp
    # This example uses system tempfile, so no custom dir is strictly needed.
    app_logger.info("Starting Flask application...")
    app.run(debug=True, port=5001) # Use a different port than Project 1 (e.g., 5001)