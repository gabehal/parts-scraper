import React from 'react';

const MakeLeaderboard = ({ leaderboard, isProcessing }) => {
  if (!leaderboard || leaderboard.length === 0) {
    return (
      <div className="card">
        <h2>Vehicle Make Leaderboard</h2>
        <div className="alert alert-info">
          {isProcessing 
            ? "Processing... Leaderboard will appear as vehicle makes are found."
            : "No vehicle makes found yet. Upload and process parts to see the leaderboard."
          }
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <h2>Vehicle Make Leaderboard</h2>
      <p style={{ fontSize: '14px', color: '#666', marginBottom: '15px' }}>
        Weighted by part quantities • Showing top {leaderboard.length} makes
      </p>
      
      <div className="leaderboard-list">
        {leaderboard.map(([make, stats], index) => (
          <div key={make} className="leaderboard-item">
            <div className="leaderboard-rank">
              #{index + 1}
            </div>
            
            <div className="leaderboard-content">
              <div className="leaderboard-make">
                {make}
              </div>
              <div className="leaderboard-stats">
                <span className="weighted-count">
                  {stats.weighted_count.toLocaleString()} units
                </span>
                <span className="part-count">
                  ({stats.count} part{stats.count !== 1 ? 's' : ''})
                </span>
              </div>
            </div>
            
            <div className="leaderboard-bar">
              <div 
                className="leaderboard-fill"
                style={{ 
                  width: `${(stats.weighted_count / leaderboard[0][1].weighted_count) * 100}%`
                }}
              ></div>
            </div>
          </div>
        ))}
      </div>
      
      {leaderboard.length >= 10 && (
        <div style={{ fontSize: '12px', color: '#999', marginTop: '10px', textAlign: 'center' }}>
          Showing top 10 makes
        </div>
      )}
    </div>
  );
};

export default MakeLeaderboard;