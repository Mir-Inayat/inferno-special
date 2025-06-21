import React, { useState, useEffect } from 'react';
import DocumentEditor from './DocumentEditor';
import './ReviewTab.css';

const ReviewTab = () => {
  const [documentsNeedingReview, setDocumentsNeedingReview] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [editingDocument, setEditingDocument] = useState(null);

  useEffect(() => {
    fetchDocumentsNeedingReview();
  }, []);

  const fetchDocumentsNeedingReview = async () => {
    try {
      setLoading(true);
      const response = await fetch('http://localhost:5000/api/documents/needs-review');
      if (!response.ok) throw new Error('Failed to fetch documents');
      const data = await response.json();
      setDocumentsNeedingReview(data.documents || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (document) => {
    setEditingDocument(document.document_id);
  };

  const handleSaveEdit = () => {
    setEditingDocument(null);
    fetchDocumentsNeedingReview(); // Refresh the list
  };

  const handleCancelEdit = () => {
    setEditingDocument(null);
  };

  const handleDelete = () => {
    setEditingDocument(null);
    fetchDocumentsNeedingReview(); // Refresh the list
  };

  const getQualityColor = (completionRate) => {
    if (completionRate >= 80) return 'high';
    if (completionRate >= 60) return 'medium';
    return 'low';
  };

  const getFileName = (filePath) => {
    if (!filePath) return 'Unknown File';
    return filePath.split('/').pop() || filePath.split('\\').pop() || 'Unknown File';
  };

  if (editingDocument) {
    return (
      <DocumentEditor
        documentId={editingDocument}
        onSave={handleSaveEdit}
        onCancel={handleCancelEdit}
        onDelete={handleDelete}
      />
    );
  }

  return (
    <div className="review-tab">
      <div className="review-header">
        <h2>Documents Needing Review</h2>
        <p className="review-subtitle">
          Documents with incomplete information or processing issues
        </p>
      </div>

      {loading ? (
        <div className="review-loading">Loading documents...</div>
      ) : error ? (
        <div className="review-error">Error: {error}</div>
      ) : documentsNeedingReview.length === 0 ? (
        <div className="no-reviews">
          <div className="no-reviews-icon">✓</div>
          <h3>All documents look good!</h3>
          <p>No documents currently need manual review.</p>
        </div>
      ) : (
        <div className="review-content">
          <div className="review-stats">
            <div className="stat-card">
              <span className="stat-number">{documentsNeedingReview.length}</span>
              <span className="stat-label">Need Review</span>
            </div>
            <div className="stat-card">
              <span className="stat-number">
                {Math.round(documentsNeedingReview.reduce((sum, doc) => sum + doc.completion_rate, 0) / documentsNeedingReview.length)}%
              </span>
              <span className="stat-label">Avg Completion</span>
            </div>
            <div className="stat-card">
              <span className="stat-number">
                {documentsNeedingReview.reduce((sum, doc) => sum + doc.na_fields, 0)}
              </span>
              <span className="stat-label">Missing Fields</span>
            </div>
          </div>

          <div className="review-list">
            {documentsNeedingReview.map((document) => (
              <div key={document.document_id} className="review-item">
                <div className="review-item-header">
                  <div className="document-info">
                    <h3 className="document-title">{getFileName(document.file_path)}</h3>
                    <div className="document-meta">
                      <span className={`document-type ${document.document_type}`}>
                        {document.document_type}
                      </span>
                      <span className={`completion-rate ${getQualityColor(document.completion_rate)}`}>
                        {Math.round(document.completion_rate)}% complete
                      </span>
                    </div>
                  </div>
                  <div className="review-actions">
                    <button 
                      className="btn-edit"
                      onClick={() => handleEdit(document)}
                    >
                      Edit & Fix
                    </button>
                  </div>
                </div>

                <div className="review-item-details">
                  <div className="completion-bar">
                    <div className="completion-bar-bg">
                      <div 
                        className={`completion-bar-fill ${getQualityColor(document.completion_rate)}`}
                        style={{ width: `${document.completion_rate}%` }}
                      ></div>
                    </div>
                    <span className="completion-text">
                      {document.total_fields - document.na_fields} of {document.total_fields} fields complete
                    </span>
                  </div>

                  <div className="issue-summary">
                    <span className="issues-label">Issues:</span>
                    <ul className="issues-list">
                      <li>{document.na_fields} fields are missing or marked as N/A</li>
                      {document.completion_rate < 50 && (
                        <li>Document may need reprocessing or manual data entry</li>
                      )}
                      {!document.summary && (
                        <li>Document summary is missing</li>
                      )}
                    </ul>
                  </div>

                  {document.summary && (
                    <div className="document-summary">
                      <strong>Summary:</strong> {document.summary}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ReviewTab;
