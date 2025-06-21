import React, { useState, useEffect } from 'react';
import './AnalyticsDashboard.css';

const AnalyticsDashboard = () => {
  const [analyticsData, setAnalyticsData] = useState(null);
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchAnalyticsData();
    fetchInsights();
  }, []);

  const fetchAnalyticsData = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/analytics/dashboard');
      if (!response.ok) throw new Error('Failed to fetch analytics');
      const data = await response.json();
      setAnalyticsData(data.data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchInsights = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/analytics/insights');
      if (!response.ok) throw new Error('Failed to fetch insights');
      const data = await response.json();
      setInsights(data);
    } catch (err) {
      console.error('Failed to fetch insights:', err);
    }
  };

  const downloadExcelReport = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/reports/excel');
      if (!response.ok) throw new Error('Failed to generate Excel report');
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `document_report_${new Date().toISOString().split('T')[0]}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      alert('Failed to download Excel report: ' + err.message);
    }
  };

  const downloadPDFReport = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/reports/pdf');
      if (!response.ok) throw new Error('Failed to generate PDF report');
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `document_analytics_${new Date().toISOString().split('T')[0]}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      alert('Failed to download PDF report: ' + err.message);
    }
  };

  if (loading) {
    return <div className="analytics-loading">Loading analytics...</div>;
  }

  if (error) {
    return <div className="analytics-error">Error: {error}</div>;
  }

  if (!analyticsData) {
    return <div className="analytics-error">No analytics data available</div>;
  }

  return (
    <div className="analytics-dashboard">
      <div className="analytics-header">
        <h2>Analytics & Reports</h2>
        <div className="report-actions">
          <button onClick={downloadExcelReport} className="btn-excel">
            📊 Download Excel Report
          </button>
          <button onClick={downloadPDFReport} className="btn-pdf">
            📄 Download PDF Report
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="summary-cards">
        <div className="summary-card">
          <div className="card-icon">📄</div>
          <div className="card-content">
            <div className="card-number">{analyticsData.summary.total_documents}</div>
            <div className="card-label">Total Documents</div>
          </div>
        </div>
        
        <div className="summary-card">
          <div className="card-icon">👥</div>
          <div className="card-content">
            <div className="card-number">{analyticsData.summary.total_users}</div>
            <div className="card-label">Active Users</div>
          </div>
        </div>
        
        <div className="summary-card">
          <div className="card-icon">💾</div>
          <div className="card-content">
            <div className="card-number">{analyticsData.summary.total_size_mb}MB</div>
            <div className="card-label">Total Storage</div>
          </div>
        </div>
        
        <div className="summary-card">
          <div className="card-icon">✅</div>
          <div className="card-content">
            <div className="card-number">{analyticsData.summary.success_rate}%</div>
            <div className="card-label">Success Rate</div>
          </div>
        </div>
        
        <div className="summary-card warning">
          <div className="card-icon">⚠️</div>
          <div className="card-content">
            <div className="card-number">{analyticsData.summary.needs_review}</div>
            <div className="card-label">Need Review</div>
          </div>
        </div>
      </div>

      <div className="analytics-grid">
        {/* Document Types Chart */}
        <div className="analytics-section">
          <h3>Document Types Distribution</h3>
          <div className="chart-container">
            <PieChart data={analyticsData.document_types} />
          </div>
        </div>

        {/* Processing Status */}
        <div className="analytics-section">
          <h3>Processing Status</h3>
          <div className="status-bars">
            {analyticsData.processing_status.labels.map((label, index) => {
              const count = analyticsData.processing_status.data[index];
              const total = analyticsData.processing_status.data.reduce((a, b) => a + b, 0);
              const percentage = ((count / total) * 100).toFixed(1);
              
              return (
                <div key={label} className="status-bar">
                  <div className="status-info">
                    <span className="status-label">{label}</span>
                    <span className="status-count">{count} ({percentage}%)</span>
                  </div>
                  <div className="progress-bar">
                    <div 
                      className={`progress-fill ${label.toLowerCase().replace(' ', '-')}`}
                      style={{ width: `${percentage}%` }}
                    ></div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Top Users */}
        <div className="analytics-section">
          <h3>Most Active Users</h3>
          <div className="top-users">
            {analyticsData.top_users.users.map((user, index) => (
              <div key={user} className="user-item">
                <div className="user-rank">#{index + 1}</div>
                <div className="user-info">
                  <div className="user-name">{user}</div>
                  <div className="user-stats">
                    {analyticsData.top_users.document_counts[index]} docs • 
                    {analyticsData.top_users.total_sizes[index]}MB
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Upload Timeline */}
        <div className="analytics-section full-width">
          <h3>Upload Activity Over Time</h3>
          <div className="timeline-chart">
            <LineChart data={analyticsData.uploads_timeline} />
          </div>
        </div>
      </div>

      {/* Insights and Suggestions */}
      {insights && (
        <div className="insights-section">
          <h3>System Insights & Recommendations</h3>
          <div className="insights-grid">
            <div className="insight-card">
              <h4>Processing Quality</h4>
              <div className="metric">
                Overall Completion: {insights.insights?.overall_completion_rate?.toFixed(1)}%
              </div>
              <div className="metric">
                Success Rate: {insights.insights?.processing_success_rate?.toFixed(1)}%
              </div>
            </div>
            
            {insights.suggestions && insights.suggestions.length > 0 && (
              <div className="suggestions-card">
                <h4>Improvement Suggestions</h4>
                <ul className="suggestions-list">
                  {insights.suggestions.map((suggestion, index) => (
                    <li key={index} className={`suggestion ${suggestion.priority}`}>
                      <div className="suggestion-text">{suggestion.suggestion}</div>
                      <div className="suggestion-metric">{suggestion.metric}</div>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

// Simple Pie Chart Component
const PieChart = ({ data }) => {
  const total = data.data.reduce((sum, value) => sum + value, 0);
  
  return (
    <div className="pie-chart">
      <div className="pie-legend">
        {data.labels.map((label, index) => {
          const percentage = ((data.data[index] / total) * 100).toFixed(1);
          return (
            <div key={label} className="legend-item">
              <div 
                className="legend-color"
                style={{ backgroundColor: data.colors[index % data.colors.length] }}
              ></div>
              <span className="legend-label">{label}</span>
              <span className="legend-value">{data.data[index]} ({percentage}%)</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// Simple Line Chart Component
const LineChart = ({ data }) => {
  const maxCount = Math.max(...data.counts);
  
  return (
    <div className="line-chart">
      <div className="chart-area">
        {data.dates.map((date, index) => {
          const height = (data.counts[index] / maxCount) * 100;
          return (
            <div key={date} className="chart-bar">
              <div 
                className="chart-bar-fill"
                style={{ height: `${height}%` }}
                title={`${date}: ${data.counts[index]} uploads`}
              ></div>
              <div className="chart-date">{date.split('-').slice(1).join('/')}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default AnalyticsDashboard;
