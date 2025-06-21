import { useState, useRef } from 'react';
import '../styles/FileUpload.css';
import { toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

const FileUpload = () => {
  const [isDragging, setIsDragging] = useState(false);
  const [files, setFiles] = useState([]);
  const [uploadStatus, setUploadStatus] = useState({});
  const [isUploading, setIsUploading] = useState(false);
  const [uploadMode, setUploadMode] = useState('single'); // 'single', 'bulk', 'folder'
  const [uploadProgress, setUploadProgress] = useState(null);
  const fileInputRef = useRef(null);
  const folderInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    
    const droppedFiles = Array.from(e.dataTransfer.files);
    handleFiles(droppedFiles);
  };

  const handleFileInput = (e) => {
    const selectedFiles = Array.from(e.target.files);
    handleFiles(selectedFiles);
  };

  const handleFolderInput = (e) => {
    const selectedFiles = Array.from(e.target.files);
    setUploadProgress({
      current: 0,
      total: selectedFiles.length,
      status: 'scanning'
    });
    handleFiles(selectedFiles);
  };

  const handleFiles = async (newFiles) => {
    // Check file sizes before processing
    const maxSize = 50 * 1024 * 1024; // 50MB in bytes
    const validFiles = [];
    
    newFiles.forEach(file => {
      if (file.size > maxSize) {
        toast.error(`File "${file.name}" is too large (${(file.size / 1024 / 1024).toFixed(1)}MB). Maximum size is 50MB.`);
        setUploadStatus(prev => ({
          ...prev,
          [file.name]: {
            status: 'error',
            message: 'File too large (max 50MB)'
          }
        }));
      } else {
        validFiles.push(file);
      }
    });

    if (validFiles.length === 0) {
      return; // No valid files to process
    }

    setFiles((prevFiles) => [...prevFiles, ...validFiles]);
    
    validFiles.forEach(file => {
      setUploadStatus(prev => ({
        ...prev,
        [file.name]: { status: 'uploading' }
      }));
    });

    const formData = new FormData();
    validFiles.forEach((file) => {
      formData.append('files[]', file);
    });

    try {
      const response = await fetch('http://localhost:5000/upload', {
        method: 'POST',
        body: formData,
        headers: {
          // Don't set Content-Type header, let browser set it for FormData
        }
      });

      if (!response.ok) {
        if (response.status === 413) {
          throw new Error('File is too large. Maximum allowed size is 50MB.');
        } else if (response.status === 404) {
          throw new Error('Upload endpoint not found. Please check server configuration.');
        } else {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.error || `Upload failed: ${response.statusText}`);
        }
      }

      const data = await response.json();
      
      if (data.error) {
        throw new Error(data.error);
      }

      // Handle successful uploads
      if (data.results && Array.isArray(data.results)) {
        let successCount = 0;
        let duplicateCount = 0;
        
        data.results.forEach((result, index) => {
          const fileName = validFiles[index]?.name || `file_${index}`;
          
          if (result.status === 'success') {
            successCount++;
            setUploadStatus(prev => ({
              ...prev,
              [fileName]: {
                status: 'success',
                message: 'Document processed successfully'
              }
            }));
          } else if (result.status === 'duplicate') {
            duplicateCount++;
            setUploadStatus(prev => ({
              ...prev,
              [fileName]: {
                status: 'duplicate',
                message: result.message || 'Document already uploaded',
                duplicateDetails: result.duplicate_details || {}
              }
            }));
          } else {
            setUploadStatus(prev => ({
              ...prev,
              [fileName]: {
                status: 'error',
                message: result.error || result.message || 'Processing failed'
              }
            }));
          }
        });
        
        // Show appropriate success message
        if (successCount > 0 && duplicateCount > 0) {
          toast.success(`${successCount} file(s) uploaded successfully. ${duplicateCount} duplicate(s) skipped.`);
        } else if (successCount > 0) {
          toast.success(`${successCount} file(s) uploaded successfully`);
        } else if (duplicateCount > 0) {
          toast.warning(`${duplicateCount} duplicate file(s) detected. These documents were already uploaded.`);
        }
      }
    } catch (error) {
      console.error('Upload error:', error);
      toast.error(error.message || 'Upload failed');
      
      validFiles.forEach(file => {
        setUploadStatus(prev => ({
          ...prev,
          [file.name]: {
            status: 'error',
            message: error.message
          }
        }));
      });
    }
  };

  const removeFile = (index) => {
    const fileToRemove = files[index];
    setFiles((prevFiles) => prevFiles.filter((_, i) => i !== index));
    setUploadStatus((prev) => {
      const newStatus = { ...prev };
      delete newStatus[fileToRemove.name];
      return newStatus;
    });
  };

  const getStatusIcon = (fileName) => {
    const status = uploadStatus[fileName]?.status;
    switch (status) {
      case 'uploading':
        return <i className="fas fa-spinner fa-spin" />;
      case 'success':
        return <i className="fas fa-check text-green-500" />;
      case 'error':
        return <i className="fas fa-exclamation-circle text-red-500" />;
      case 'duplicate':
        return <i className="fas fa-copy text-yellow-500" />;
      default:
        return null;
    }
  };

  const allFilesUploaded = files.length > 0 && files.every(file => uploadStatus[file.name]?.status === 'success');

  const handleSubmit = async () => {
    if (files.length === 0) {
      toast.warning('Please select files to upload');
      return;
    }
    
    setIsUploading(true);
    const formData = new FormData();
    files.forEach(file => {
        formData.append('files[]', file);
    });

    try {
        const response = await fetch('http://localhost:5000/upload', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
          throw new Error(`Upload failed: ${response.statusText}`);
        }
        
        const data = await response.json();
        if (data.error) {
            throw new Error(data.error);
        }
        
        setFiles([]);
        toast.success('Files submitted successfully');
        window.location.href = '/dashboard';
    } catch (error) {
        console.error('Submit error:', error);
        toast.error(error.message || 'Submit failed');
    } finally {
        setIsUploading(false);
    }
  };

  return (
    <div className="file-upload-container">
      {/* Upload Mode Selection */}
      <div className="upload-mode-selector">
        <button 
          className={`mode-btn ${uploadMode === 'single' ? 'active' : ''}`}
          onClick={() => setUploadMode('single')}
        >
          Single Files
        </button>
        <button 
          className={`mode-btn ${uploadMode === 'bulk' ? 'active' : ''}`}
          onClick={() => setUploadMode('bulk')}
        >
          Bulk Upload
        </button>
        <button 
          className={`mode-btn ${uploadMode === 'folder' ? 'active' : ''}`}
          onClick={() => setUploadMode('folder')}
        >
          Folder Upload
        </button>
      </div>

      <div
        className={`drop-zone ${isDragging ? 'dragging' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => {
          if (uploadMode === 'folder') {
            folderInputRef.current?.click();
          } else {
            fileInputRef.current?.click();
          }
        }}
      >
        <div className="drop-zone-content">
          <i className="fas fa-cloud-upload-alt"></i>
          <p>
            {uploadMode === 'folder' 
              ? 'Drag and drop folders here or click to select'
              : uploadMode === 'bulk'
              ? 'Drag and drop multiple files or ZIP archives'
              : 'Drag and drop files here or click to select'
            }
          </p>
          <span className="supported-files">
            {uploadMode === 'folder' 
              ? 'Recursively processes all supported files in folders'
              : 'Supports PDF, Images, Text files, and ZIP archives'
            }
          </span>
        </div>
        
        {/* Regular file input */}
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileInput}
          multiple={uploadMode !== 'single'}
          accept=".pdf,.jpg,.jpeg,.png,.tiff,.txt,.zip"
          hidden
        />
        
        {/* Folder input */}
        <input
          type="file"
          ref={folderInputRef}
          onChange={handleFolderInput}
          webkitdirectory="true"
          multiple
          hidden
        />
      </div>

      {files.length > 0 && (
        <div className="file-list">
          {uploadProgress && (
            <div className="upload-progress">
              <div className="progress-bar">
                <div 
                  className="progress-fill" 
                  style={{ 
                    width: `${(uploadProgress.current / uploadProgress.total) * 100}%` 
                  }}
                ></div>
              </div>
              <span className="progress-text">
                {uploadProgress.status === 'scanning' ? 'Scanning files...' : 'Uploading...'} 
                {uploadProgress.current}/{uploadProgress.total}
              </span>
            </div>
          )}
          
          {files.map((file, index) => (
            <div key={index} className="file-item">
              <div className="file-info">
                <span className="file-name">{file.name}</span>
                <span className="file-path">{file.webkitRelativePath || file.name}</span>
                {uploadStatus[file.name]?.message && (
                  <span className={`file-${uploadStatus[file.name]?.status || 'error'}`}>
                    {uploadStatus[file.name].message}
                  </span>
                )}
              </div>
              <div className="file-actions">
                {getStatusIcon(file.name)}
                <button
                  className="remove-file"
                  onClick={() => removeFile(index)}
                >
                  ×
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="submit-section">
        <button 
          className="submit-button"
          onClick={handleSubmit}
          disabled={files.length === 0 || isUploading}
        >
          {isUploading ? (
            <span>Uploading... <i className="fas fa-spinner fa-spin"></i></span>
          ) : (
            <span>Upload Files</span>
          )}
        </button>
      </div>

      {allFilesUploaded && (
        <button className="submit-button" onClick={handleSubmit}>
          Submit
        </button>
      )}
    </div>
  );
};

export default FileUpload;