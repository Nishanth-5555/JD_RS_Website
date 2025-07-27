// src/components/ResumeScreener.js

import React, { useState } from 'react';
import axios from 'axios';

function ResumeScreener({ jobDescription, setLoading, setErrorMessage, onCandidatesScreened }) {
  const [resumeFiles, setResumeFiles] = useState([]);
  const [processingMessage, setProcessingMessage] = useState('');

  const handleFileChange = (e) => {
    setResumeFiles(Array.from(e.target.files)); // Convert FileList to Array
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage('');
    if (!jobDescription) {
      setErrorMessage('Please generate or provide a Job Description first.');
      return;
    }
    if (resumeFiles.length === 0) {
      setErrorMessage('Please select resume files to upload.');
      return;
    }

    setLoading(true);
    setProcessingMessage('Uploading resumes and screening...');

    const formData = new FormData();
    formData.append('job_description', jobDescription);
    resumeFiles.forEach((file, index) => {
      formData.append(`resume_files`, file); // Key must match Flask's request.files.getlist()
    });

    try {
      // Ensure your Resume Screener Flask API is running on this port
      const response = await axios.post('http://localhost:5001/screen_resumes', formData, {
        headers: {
          'Content-Type': 'multipart/form-data', // Important for file uploads
        },
      });

      if (response.status === 200) {
        setProcessingMessage('Screening complete!');
        onCandidatesScreened(response.data.candidates); // Pass to parent (App.js)
      } else {
        setErrorMessage(response.data.error || 'Failed to screen resumes.');
      }
    } catch (error) {
      console.error('Error screening resumes:', error);
      setErrorMessage(error.response?.data?.error || error.message || 'Network error screening resumes.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="form-section">
      <h2>Resume Screener 📄</h2>
      {jobDescription ? (
        <>
          <p>Job Description ready for screening. Upload resumes below.</p>
          <form onSubmit={handleSubmit}>
            <div className="input-group">
              <label htmlFor="resumeFiles" className="file-upload-btn">
                📂 Select Resumes
              </label>
              <input 
                id="resumeFiles" 
                type="file" 
                multiple 
                accept=".pdf,.docx,.txt" 
                onChange={handleFileChange} 
                style={{ display: 'none' }} // Hide native input
              />
              {resumeFiles.length > 0 && (
                <span className="selected-file-name">
                  {resumeFiles.length} file(s) selected: {resumeFiles.map(f => f.name).join(', ')}
                </span>
              )}
            </div>
            <div className="input-group">
              <button type="submit">🔍 Screen Resumes</button>
            </div>
          </form>
          {processingMessage && <p className="loading-message">{processingMessage}</p>}
        </>
      ) : (
        <p>Please generate a Job Description first to enable resume screening.</p>
      )}
    </div>
  );
}

export default ResumeScreener;