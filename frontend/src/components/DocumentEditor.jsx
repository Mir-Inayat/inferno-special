import React, { useState, useEffect } from 'react';
import './DocumentEditor.css';

const DocumentEditor = ({ documentId, onSave, onCancel, onDelete }) => {
  const [documentData, setDocumentData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    fetchDocumentData();
  }, [documentId]);

  const fetchDocumentData = async () => {
    try {
      setLoading(true);
      const response = await fetch(`http://localhost:5000/api/documents/${documentId}/edit`);
      if (!response.ok) throw new Error('Failed to fetch document data');
      const data = await response.json();
      setDocumentData(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleFieldChange = (category, field, value) => {
    setDocumentData(prev => ({
      ...prev,
      [category]: {
        ...prev[category],
        [field]: value
      }
    }));
    setHasChanges(true);
  };

  const handleDocumentFieldChange = (field, value) => {
    setDocumentData(prev => ({
      ...prev,
      fields: {
        ...prev.fields,
        [field]: value
      }
    }));
    setHasChanges(true);
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      const response = await fetch(`http://localhost:5000/api/documents/${documentId}/edit`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          document_type: documentData.document_type,
          sub_category: documentData.sub_category,
          summary: documentData.summary,
          notes: documentData.notes,
          person: documentData.person,
          fields: documentData.fields
        })
      });

      if (!response.ok) throw new Error('Failed to save changes');
      
      setHasChanges(false);
      onSave && onSave();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete this document? This action cannot be undone.')) {
      return;
    }

    try {
      const response = await fetch(`http://localhost:5000/api/documents/${documentId}`, {
        method: 'DELETE'
      });

      if (!response.ok) throw new Error('Failed to delete document');
      
      onDelete && onDelete();
    } catch (err) {
      setError(err.message);
    }
  };

  if (loading) return <div className="editor-loading">Loading document data...</div>;
  if (error) return <div className="editor-error">Error: {error}</div>;
  if (!documentData) return <div className="editor-error">No document data found</div>;

  return (
    <div className="document-editor">
      <div className="editor-header">
        <h2>Edit Document</h2>
        <div className="editor-actions">
          <button 
            className="btn-save" 
            onClick={handleSave} 
            disabled={!hasChanges || saving}
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
          <button className="btn-cancel" onClick={onCancel}>Cancel</button>
          <button className="btn-delete" onClick={handleDelete}>Delete</button>
        </div>
      </div>

      {error && <div className="editor-error">{error}</div>}

      <div className="editor-content">
        {/* Document Basic Info */}
        <div className="editor-section">
          <h3>Document Information</h3>
          <div className="form-grid">
            <div className="form-group">
              <label>Document Type</label>
              <select 
                value={documentData.document_type || ''} 
                onChange={(e) => handleFieldChange('', 'document_type', e.target.value)}
              >
                <option value="">Select Type</option>
                <option value="passport">Passport</option>
                <option value="visa">Visa</option>
                <option value="emirates_id">Emirates ID</option>
                <option value="driving_license">Driving License</option>
                <option value="residence_visa">Residence Visa</option>
                <option value="work_permit">Work Permit</option>
                <option value="certificate">Certificate</option>
                <option value="inspection_certificate">Inspection Certificate</option>
                <option value="other">Other</option>
              </select>
            </div>
            
            <div className="form-group">
              <label>Sub-category</label>
              <input 
                type="text" 
                value={documentData.sub_category || ''} 
                onChange={(e) => handleFieldChange('', 'sub_category', e.target.value)}
                placeholder="Enter sub-category"
              />
            </div>
            
            <div className="form-group full-width">
              <label>Summary</label>
              <textarea 
                value={documentData.summary || ''} 
                onChange={(e) => handleFieldChange('', 'summary', e.target.value)}
                placeholder="Document summary"
                rows="3"
              />
            </div>
            
            <div className="form-group full-width">
              <label>Notes</label>
              <textarea 
                value={documentData.notes || ''} 
                onChange={(e) => handleFieldChange('', 'notes', e.target.value)}
                placeholder="Additional notes"
                rows="2"
              />
            </div>
          </div>
        </div>

        {/* Personal Information */}
        <div className="editor-section">
          <h3>Personal Information</h3>
          <div className="form-grid">
            <div className="form-group">
              <label>Full Name</label>
              <input 
                type="text" 
                value={documentData.person?.name || ''} 
                onChange={(e) => handleFieldChange('person', 'name', e.target.value)}
                placeholder="Enter full name"
              />
            </div>
            
            <div className="form-group">
              <label>Nationality</label>
              <input 
                type="text" 
                value={documentData.person?.nationality || ''} 
                onChange={(e) => handleFieldChange('person', 'nationality', e.target.value)}
                placeholder="Enter nationality"
              />
            </div>
            
            <div className="form-group">
              <label>Gender</label>
              <select 
                value={documentData.person?.gender || ''} 
                onChange={(e) => handleFieldChange('person', 'gender', e.target.value)}
              >
                <option value="">Select Gender</option>
                <option value="Male">Male</option>
                <option value="Female">Female</option>
                <option value="Other">Other</option>
              </select>
            </div>
            
            <div className="form-group">
              <label>Date of Birth</label>
              <input 
                type="date" 
                value={documentData.person?.date_of_birth || ''} 
                onChange={(e) => handleFieldChange('person', 'date_of_birth', e.target.value)}
              />
            </div>
          </div>
        </div>

        {/* Document Fields */}
        <div className="editor-section">
          <h3>Document Fields</h3>
          <div className="fields-grid">
            {Object.entries(documentData.fields || {}).map(([fieldName, fieldValue]) => (
              <div key={fieldName} className="form-group">
                <label>{fieldName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</label>
                <input 
                  type="text" 
                  value={fieldValue || ''} 
                  onChange={(e) => handleDocumentFieldChange(fieldName, e.target.value)}
                  placeholder={`Enter ${fieldName.replace(/_/g, ' ')}`}
                />
              </div>
            ))}
          </div>
        </div>

        {/* Add Custom Field */}
        <div className="editor-section">
          <h3>Add Custom Field</h3>
          <CustomFieldAdder onAdd={(name, value) => handleDocumentFieldChange(name, value)} />
        </div>
      </div>
    </div>
  );
};

const CustomFieldAdder = ({ onAdd }) => {
  const [fieldName, setFieldName] = useState('');
  const [fieldValue, setFieldValue] = useState('');

  const handleAdd = () => {
    if (fieldName.trim() && fieldValue.trim()) {
      onAdd(fieldName.trim(), fieldValue.trim());
      setFieldName('');
      setFieldValue('');
    }
  };

  return (
    <div className="custom-field-adder">
      <div className="form-row">
        <input 
          type="text" 
          placeholder="Field name" 
          value={fieldName} 
          onChange={(e) => setFieldName(e.target.value)}
        />
        <input 
          type="text" 
          placeholder="Field value" 
          value={fieldValue} 
          onChange={(e) => setFieldValue(e.target.value)}
        />
        <button onClick={handleAdd} disabled={!fieldName.trim() || !fieldValue.trim()}>
          Add Field
        </button>
      </div>
    </div>
  );
};

export default DocumentEditor;
