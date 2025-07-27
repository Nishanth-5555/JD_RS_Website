// src/App.js

import React, { useState } from 'react';
import './App.css'; // Your main CSS
import JobDescriptionBuilder from './components/JobDescriptionBuilder';
import ResumeScreener from './components/ResumeScreener';
import ResultsDisplay from './components/ResultsDisplay';

function App() {
  const [generatedJobDescription, setGeneratedJobDescription] = useState('');
  const [screenedCandidates, setScreenedCandidates] = useState([]);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  return (
    <div className="app-container">
      <h1>AI-Powered HR Assistant 🤖</h1>

      {/* JD Builder Section */}
      <JobDescriptionBuilder
        onJobDescriptionGenerated={setGeneratedJobDescription}
        setLoading={setLoading}
        setErrorMessage={setErrorMessage}
      />

      {/* Resume Screener Section */}
      <ResumeScreener
        jobDescription={generatedJobDescription}
        setLoading={setLoading}
        setErrorMessage={setErrorMessage}
        onCandidatesScreened={setScreenedCandidates}
      />

      {loading && <p className="loading-message">Processing your request...</p>}
      {errorMessage && <p className="error-message">{errorMessage}</p>}

      {/* Results Display Section */}
      {screenedCandidates.length > 0 && (
        <div className="results-container">
          <ResultsDisplay candidates={screenedCandidates} />
        </div>
      )}
    </div>
  );
}

export default App;