import React, { useState, useEffect, useMemo } from 'react';
import DocumentCard from '../components/DocumentCard';
import DocumentEditor from '../components/DocumentEditor';
import ReviewTab from '../components/ReviewTab';
import AnalyticsDashboard from '../components/AnalyticsDashboard';
import './Dashboard.css';

const LANGUAGES = {
  'en': 'English',
  'ta': 'Tamil',
  'te': 'Telugu',
  'hi': 'Hindi',
  'ur': 'Urdu',
  'ar': 'Arabic',
  'fr': 'French',
  'es': 'Spanish'
};

const DOCUMENT_CATEGORIES = {
  'all': 'All Documents',
  'passport': 'Passports',
  'visa': 'Visas',
  'emirates_id': 'Emirates ID',
  'driving_license': 'Driving Licenses',
  'residence_visa': 'Residence Visas',
  'work_permit': 'Work Permits',
  'certificate': 'Certificates',
  'inspection_certificate': 'Inspection Certificates',
  'other': 'Other Documents'
};

const Dashboard = () => {
  const [documentData, setDocumentData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedLanguage, setSelectedLanguage] = useState('en');
  const [translations, setTranslations] = useState({});
  
  // Enhanced dashboard state
  const [searchTerm, setSearchTerm] = useState('');
  const [sortConfig, setSortConfig] = useState({ key: 'created_at', direction: 'desc' });
  const [viewMode, setViewMode] = useState('cards'); // 'cards' or 'table'
  const [activeTab, setActiveTab] = useState('all');
  const [mainTab, setMainTab] = useState('documents'); // 'documents', 'review', 'analytics', 'editor'
  const [groupBy, setGroupBy] = useState('none'); // 'none', 'user', 'type', 'date'
  const [bulkUploadProgress, setBulkUploadProgress] = useState(null);
  const [selectedDocumentId, setSelectedDocumentId] = useState(null);

  // Utility functions
  const translateText = async (text, language) => {
    if (!text || language === 'en') return text;
    
    const cacheKey = `${text}-${language}`;
    if (translations[cacheKey]) return translations[cacheKey];

    try {
      const response = await fetch('http://localhost:5000/api/translate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, target_language: language })
      });
      const data = await response.json();
      
      if (data.error) throw new Error(data.error);
      
      setTranslations(prev => ({
        ...prev,
        [cacheKey]: data.translatedText
      }));
      
      return data.translatedText;
    } catch (error) {
      console.error('Translation error:', error);
      return text;
    }
  };

  // Enhanced data processing
  const processedDocuments = useMemo(() => {
    let filtered = documentData;

    // Filter by active tab (category)
    if (activeTab !== 'all') {
      filtered = filtered.filter(doc => doc.primary_category === activeTab);
    }

    // Filter by search term
    if (searchTerm) {
      const searchLower = searchTerm.toLowerCase();
      filtered = filtered.filter(doc => 
        doc.file_path?.toLowerCase().includes(searchLower) ||
        doc.person?.name?.toLowerCase().includes(searchLower) ||
        doc.primary_category?.toLowerCase().includes(searchLower) ||
        doc.sub_category?.toLowerCase().includes(searchLower) ||
        doc.summary?.toLowerCase().includes(searchLower)
      );
    }

    // Sort documents
    filtered.sort((a, b) => {
      let aVal = a[sortConfig.key];
      let bVal = b[sortConfig.key];

      // Handle nested values
      if (sortConfig.key === 'person_name') {
        aVal = a.person?.name || '';
        bVal = b.person?.name || '';
      } else if (sortConfig.key === 'file_name') {
        aVal = a.file_path ? a.file_path.split('/').pop() : '';
        bVal = b.file_path ? b.file_path.split('/').pop() : '';
      } else if (sortConfig.key === 'file_size') {
        aVal = a.file_size || 0;
        bVal = b.file_size || 0;
      }

      if (aVal === null || aVal === undefined) aVal = '';
      if (bVal === null || bVal === undefined) bVal = '';

      if (typeof aVal === 'string' && typeof bVal === 'string') {
        aVal = aVal.toLowerCase();
        bVal = bVal.toLowerCase();
      }

      if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });

    return filtered;
  }, [documentData, activeTab, searchTerm, sortConfig]);

  // Group documents
  const groupedDocuments = useMemo(() => {
    if (groupBy === 'none') {
      return { 'All Documents': processedDocuments };
    }

    const groups = {};
    processedDocuments.forEach(doc => {
      let groupKey;
      switch (groupBy) {
        case 'user':
          groupKey = doc.person?.name || 'Unknown User';
          break;
        case 'type':
          groupKey = doc.primary_category || 'Unknown Type';
          break;
        case 'date': {
          const date = new Date(doc.created_at);
          groupKey = date.toLocaleDateString();
          break;
        }
        default:
          groupKey = 'All Documents';
      }
      
      if (!groups[groupKey]) groups[groupKey] = [];
      groups[groupKey].push(doc);
    });

    return groups;
  }, [processedDocuments, groupBy]);

  // Event handlers
  const handleSort = (key) => {
    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc'
    }));
  };

  const handleBulkUpload = async (files) => {
    setBulkUploadProgress({ current: 0, total: files.length });
    
    for (let i = 0; i < files.length; i++) {
      const formData = new FormData();
      formData.append('file', files[i]);
      
      try {
        await fetch('http://localhost:5000/api/upload', {
          method: 'POST',
          body: formData
        });
        setBulkUploadProgress({ current: i + 1, total: files.length });
      } catch (error) {
        console.error(`Failed to upload ${files[i].name}:`, error);
      }
    }
    
    setBulkUploadProgress(null);
    // Refresh documents
    fetchDocuments();
  };

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      const response = await fetch('http://localhost:5000/api/documents');
      if (!response.ok) throw new Error('Failed to fetch documents');
      const data = await response.json();
      setDocumentData(data.documents);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return 'N/A';
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const renderTableView = () => (
    <div className="table-container">
      <table className="documents-table">
        <thead>
          <tr>
            <th onClick={() => handleSort('file_name')} className="sortable">
              File Name {sortConfig.key === 'file_name' && (
                <span className={`sort-arrow ${sortConfig.direction}`}>
                  {sortConfig.direction === 'asc' ? '↑' : '↓'}
                </span>
              )}
            </th>
            <th onClick={() => handleSort('primary_category')} className="sortable">
              Type {sortConfig.key === 'primary_category' && (
                <span className={`sort-arrow ${sortConfig.direction}`}>
                  {sortConfig.direction === 'asc' ? '↑' : '↓'}
                </span>
              )}
            </th>
            <th onClick={() => handleSort('person_name')} className="sortable">
              Person {sortConfig.key === 'person_name' && (
                <span className={`sort-arrow ${sortConfig.direction}`}>
                  {sortConfig.direction === 'asc' ? '↑' : '↓'}
                </span>
              )}
            </th>
            <th onClick={() => handleSort('file_size')} className="sortable">
              Size {sortConfig.key === 'file_size' && (
                <span className={`sort-arrow ${sortConfig.direction}`}>
                  {sortConfig.direction === 'asc' ? '↑' : '↓'}
                </span>
              )}
            </th>
            <th onClick={() => handleSort('created_at')} className="sortable">
              Upload Date {sortConfig.key === 'created_at' && (
                <span className={`sort-arrow ${sortConfig.direction}`}>
                  {sortConfig.direction === 'asc' ? '↑' : '↓'}
                </span>
              )}
            </th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(groupedDocuments).map(([groupName, docs]) => (
            <React.Fragment key={groupName}>
              {groupBy !== 'none' && (
                <tr className="group-header">
                  <td colSpan="6">
                    <strong>{groupName} ({docs.length} documents)</strong>
                  </td>
                </tr>
              )}
              {docs.map(doc => (
                <tr key={doc.id} className="document-row">
                  <td className="file-name">
                    {doc.file_path ? doc.file_path.split('/').pop() : 'Unknown'}
                  </td>
                  <td className="document-type">
                    <span className={`type-badge ${doc.primary_category}`}>
                      {doc.primary_category || 'Unknown'}
                    </span>
                  </td>
                  <td className="person-name">
                    {doc.person?.name || 'N/A'}
                  </td>
                  <td className="file-size">
                    {formatFileSize(doc.file_size)}
                  </td>
                  <td className="upload-date">
                    {new Date(doc.created_at).toLocaleDateString()}
                  </td>
                  <td className="actions">
                    <button 
                      className="view-btn"
                      onClick={() => window.open(`http://localhost:5000/api/document/${doc.id}/file`, '_blank')}
                    >
                      View
                    </button>
                  </td>
                </tr>
              ))}
            </React.Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );

  const renderCardView = () => (
    <div className="documents-container">
      {Object.entries(groupedDocuments).map(([groupName, docs]) => (
        <div key={groupName} className="document-group">
          {groupBy !== 'none' && (
            <h3 className="group-title">{groupName} ({docs.length} documents)</h3>
          )}
          <div className="documents-grid">
            {docs.map(doc => (
              <DocumentCard 
                key={doc.id}
                doc={doc}
                selectedLanguage={selectedLanguage}
                translateText={translateText}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );

  return (
    <div className="dashboard-container">
      <div className="dashboard-header">
        <div className="header-content">
          <h1>Advanced Document Management Dashboard</h1>
          <div className="header-stats">
            <span className="stat">
              Total: {documentData.length} documents
            </span>
            <span className="stat">
              Filtered: {processedDocuments.length} documents
            </span>
          </div>
        </div>
      </div>

      {/* Language Selection */}
      <div className="language-section">
        <span className="language-label">Choose Language:</span>
        <select 
          value={selectedLanguage}
          onChange={(e) => setSelectedLanguage(e.target.value)}
          className="language-selector"
        >
          {Object.entries(LANGUAGES).map(([code, name]) => (
            <option key={code} value={code}>{name}</option>
          ))}
        </select>
      </div>

      {/* Category Tabs */}
      <div className="category-tabs">
        {Object.entries(DOCUMENT_CATEGORIES).map(([key, label]) => (
          <button
            key={key}
            className={`tab-button ${activeTab === key ? 'active' : ''}`}
            onClick={() => setActiveTab(key)}
          >
            {label}
            {key !== 'all' && (
              <span className="tab-count">
                ({documentData.filter(doc => doc.primary_category === key).length})
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Controls */}
      <div className="dashboard-controls">
        <div className="search-section">
          <input
            type="text"
            placeholder="Search documents, people, or content..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
        </div>

        <div className="view-controls">
          <div className="view-mode">
            <button
              className={`mode-btn ${viewMode === 'cards' ? 'active' : ''}`}
              onClick={() => setViewMode('cards')}
            >
              Cards
            </button>
            <button
              className={`mode-btn ${viewMode === 'table' ? 'active' : ''}`}
              onClick={() => setViewMode('table')}
            >
              Table
            </button>
          </div>

          <div className="group-controls">
            <label>Group by:</label>
            <select value={groupBy} onChange={(e) => setGroupBy(e.target.value)}>
              <option value="none">No Grouping</option>
              <option value="user">User/Person</option>
              <option value="type">Document Type</option>
              <option value="date">Upload Date</option>
            </select>
          </div>

          <div className="bulk-upload">
            <input
              type="file"
              multiple
              accept=".pdf,.jpg,.jpeg,.png,.tiff,.txt"
              onChange={(e) => handleBulkUpload(Array.from(e.target.files))}
              style={{ display: 'none' }}
              id="bulk-upload"
            />
            <label htmlFor="bulk-upload" className="bulk-upload-btn">
              Bulk Upload
            </label>
            {bulkUploadProgress && (
              <div className="upload-progress">
                Uploading: {bulkUploadProgress.current}/{bulkUploadProgress.total}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div className="loading">Loading documents...</div>
      ) : error ? (
        <div className="error">Error: {error}</div>
      ) : (
        <>
          {processedDocuments.length === 0 ? (
            <div className="no-documents">
              {searchTerm ? `No documents found matching "${searchTerm}"` : 'No documents found'}
            </div>
          ) : (
            viewMode === 'table' ? renderTableView() : renderCardView()
          )}
        </>
      )}
    </div>
  );
};

export default Dashboard;