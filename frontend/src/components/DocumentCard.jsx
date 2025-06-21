import React, { useState, useEffect } from 'react';

const DocumentCard = ({ doc, selectedLanguage, translateText }) => {
  const [translatedContent, setTranslatedContent] = useState(doc);
  const [translating, setTranslating] = useState(false);

  useEffect(() => {
    const translateContent = async () => {
      if (selectedLanguage === 'en') {
        setTranslatedContent(doc);
        return;
      }
      
      setTranslating(true);
      const translated = {
        ...doc,
        file_name: await translateText(doc.file_name, selectedLanguage),
        primary_category: await translateText(doc.primary_category, selectedLanguage),
        sub_category: await translateText(doc.sub_category, selectedLanguage),
        summary: await translateText(doc.summary, selectedLanguage)
      };
      setTranslatedContent(translated);
      setTranslating(false);
    };
    
    translateContent();
  }, [selectedLanguage, doc, translateText]);

  return (
    <div className="dashboard-card">
      {translating ? (
        <div className="translating-overlay">
          <p>Translating...</p>
        </div>
      ) : (
        <>
          <div className="card-header">
            <h2>{translatedContent.file_name}</h2>
            <span className="document-type">{translatedContent.primary_category}</span>
          </div>
          
          <div className="card-section">
            <h3>Personal Information</h3>
            <div className="info-grid">
              <p><strong>Name:</strong> {doc.person?.personal?.name || doc.person?.name || 'N/A'}</p>
              <p><strong>Nationality:</strong> {doc.person?.personal?.nationality || doc.person?.nationality || 'N/A'}</p>
              <p><strong>Gender:</strong> {doc.person?.personal?.gender || doc.person?.gender || 'N/A'}</p>
              <p><strong>Date of Birth:</strong> {doc.person?.personal?.date_of_birth || 'N/A'}</p>
              <p><strong>Profession:</strong> {doc.person?.personal?.profession || doc.person?.profession || 'N/A'}</p>
            </div>
          </div>

          <div className="card-section">
            <h3>Document Identifiers</h3>
            <div className="info-grid">
              {doc.person?.document?.id_number !== 'N/A' && (
                <p><strong>Emirates ID:</strong> {doc.person.document.id_number}</p>
              )}
              {doc.person?.document?.passport_number !== 'N/A' && (
                <p><strong>Passport:</strong> {doc.person.document.passport_number}</p>
              )}
              {doc.person?.document?.visa_number !== 'N/A' && (
                <p><strong>Visa Number:</strong> {doc.person.document.visa_number}</p>
              )}
              {doc.person?.document?.license_number !== 'N/A' && (
                <p><strong>License:</strong> {doc.person.document.license_number}</p>
              )}
              {doc.person?.document?.file_number !== 'N/A' && (
                <p><strong>File Number:</strong> {doc.person.document.file_number}</p>
              )}
            </div>
          </div>

          <div className="card-section">
            <h3>Document Details</h3>
            <div className="info-grid">
              <p><strong>Category:</strong> {translatedContent.primary_category}</p>
              <p><strong>Sub-category:</strong> {translatedContent.sub_category}</p>
              <p><strong>Issue Date:</strong> {doc.person?.dates?.issue_date || 'N/A'}</p>
              <p><strong>Expiry Date:</strong> {doc.person?.dates?.expiry_date || 'N/A'}</p>
              <p><strong>Issuing Authority:</strong> {doc.person?.dates?.issuing_authority || 'N/A'}</p>
              <p><strong>Place of Issue:</strong> {doc.person?.dates?.place_of_issue || 'N/A'}</p>
              <p><strong>File Size:</strong> {doc.file_size ? `${(doc.file_size / 1024).toFixed(1)} KB` : 'N/A'}</p>
              <p><strong>Status:</strong> {doc.processing_status || 'N/A'}</p>
            </div>
          </div>

          {(doc.person?.employment?.employer_name !== 'N/A' || 
            doc.person?.employment?.sponsor_name !== 'N/A' || 
            doc.person?.employment?.job_title !== 'N/A') && (
            <div className="card-section">
              <h3>Employment Information</h3>
              <div className="info-grid">
                {doc.person?.employment?.employer_name !== 'N/A' && (
                  <p><strong>Employer:</strong> {doc.person.employment.employer_name}</p>
                )}
                {doc.person?.employment?.sponsor_name !== 'N/A' && (
                  <p><strong>Sponsor:</strong> {doc.person.employment.sponsor_name}</p>
                )}
                {doc.person?.employment?.job_title !== 'N/A' && (
                  <p><strong>Job Title:</strong> {doc.person.employment.job_title}</p>
                )}
              </div>
            </div>
          )}

          {doc.person?.additional && Object.keys(doc.person.additional).length > 0 && (
            <div className="card-section">
              <h3>Additional Information</h3>
              <div className="info-grid">
                {Object.entries(doc.person.additional).map(([key, value]) => (
                  <p key={key}><strong>{key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:</strong> {value}</p>
                ))}
              </div>
            </div>
          )}

          {translatedContent.summary && (
            <div className="card-section">
              <h3>Summary</h3>
              <p>{translatedContent.summary}</p>
            </div>
          )}

          <div className="card-actions">
            <button onClick={() => window.open(`http://localhost:5000/download/${doc.id}`)}>
              View Document
            </button>
          </div>
        </>
      )}
    </div>
  );
};

export default DocumentCard;