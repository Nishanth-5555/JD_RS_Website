// src/components/ResultsDisplay.js

import React from 'react';

function ResultsDisplay({ candidates }) {
  if (!candidates || candidates.length === 0) {
    return null; // Don't render if no candidates
  }

  // Emojis for candidate items (optional)
  const candidateEmojis = ["🌟", "✅", "✨", "👍", "💡"];

  return (
    <div className="results-panel">
      <h2>Screening Results 📊</h2>
      <ul className="candidate-list">
        {candidates.map((candidate, index) => (
          <li key={candidate.id || index} className="candidate-item">
            <h3>
                <span className="candidate-emoji">{candidateEmojis[index % candidateEmojis.length]}</span>
                {candidate.name || candidate.filename}
            </h3>
            <p><span className="score">Score: {candidate.score}%</span></p>
            <p><strong>Reasoning:</strong> {candidate.reasoning}</p>
            <p><strong>Extracted Skills:</strong> {candidate.extracted_skills ? candidate.extracted_skills.join(', ') : 'N/A'}</p>
            {/* You can add more parsed data here */}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default ResultsDisplay;