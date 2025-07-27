// src/components/JobDescriptionBuilder.js

import React, { useState } from 'react';
import axios from 'axios'; // Using axios for simpler POST requests

function JobDescriptionBuilder({ onJobDescriptionGenerated, setLoading, setErrorMessage }) {
  const [jobTitle, setJobTitle] = useState('');
  const [department, setDepartment] = useState('');
  const [responsibilities, setResponsibilities] = useState('');
  const [skills, setSkills] = useState('');
  const [experience, setExperience] = useState('');
  const [qualifications, setQualifications] = useState('');
  const [location, setLocation] = useState('');
  const [generatedJobDescription, setGeneratedJobDescription] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage('');
    setLoading(true);
    setGeneratedJobDescription(''); // Clear previous JD

    const jdData = {
      job_title: jobTitle,
      department: department,
      responsibilities: responsibilities,
      skills: skills,
      experience: experience,
      qualifications: qualifications,
      location: location,
      tone: "Professional, inspiring, and inclusive" // Hardcoded tone for now
    };

    try {
      // Ensure your JD Builder Flask API is running on this port
      const response = await axios.post('http://localhost:5000/generate_jd', jdData);
      
      if (response.status === 200) {
        const jd = response.data.job_description;
        setGeneratedJobDescription(jd);
        onJobDescriptionGenerated(jd); // Pass to parent (App.js)
      } else {
        setErrorMessage(response.data.error || 'Failed to generate Job Description.');
      }
    } catch (error) {
      console.error('Error generating JD:', error);
      setErrorMessage(error.response?.data?.error || error.message || 'Network error generating JD.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="form-section">
      <h2>Job Description Builder 📝</h2>
      <form onSubmit={handleSubmit}>
        <div className="input-group">
          <label htmlFor="jobTitle">Job Title:</label>
          <input type="text" id="jobTitle" value={jobTitle} onChange={(e) => setJobTitle(e.target.value)} required />
        </div>
        <div className="input-group">
          <label htmlFor="department">Department:</label>
          <input type="text" id="department" value={department} onChange={(e) => setDepartment(e.target.value)} required />
        </div>
        <div className="input-group">
          <label htmlFor="responsibilities">Key Responsibilities:</label>
          <textarea id="responsibilities" value={responsibilities} onChange={(e) => setResponsibilities(e.target.value)} rows="4" required />
        </div>
        <div className="input-group">
          <label htmlFor="skills">Required Skills (comma-separated):</label>
          <input type="text" id="skills" value={skills} onChange={(e) => setSkills(e.target.value)} required />
        </div>
        <div className="input-group">
          <label htmlFor="experience">Required Experience (e.g., "5+ years"):</label>
          <input type="text" id="experience" value={experience} onChange={(e) => setExperience(e.target.value)} required />
        </div>
        <div className="input-group">
          <label htmlFor="qualifications">Qualifications (e.g., "B.Tech in CS"):</label>
          <input type="text" id="qualifications" value={qualifications} onChange={(e) => setQualifications(e.target.value)} required />
        </div>
        <div className="input-group">
          <label htmlFor="location">Location:</label>
          <input type="text" id="location" value={location} onChange={(e) => setLocation(e.target.value)} required />
        </div>
        <div className="input-group">
          <button type="submit">Generate JD</button>
        </div>
      </form>
      {generatedJobDescription && (
        <div className="job-description-output">
          <h3>Generated Job Description:</h3>
          <pre>{generatedJobDescription}</pre> {/* Using <pre> to preserve whitespace from LLM */}
        </div>
      )}
    </div>
  );
}

export default JobDescriptionBuilder;