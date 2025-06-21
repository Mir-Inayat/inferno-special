import React from 'react';
import FileUpload from '../components/FileUpload';
import './Home.css';

const Home = () => {
  return (
    <div className="container">
      <div className="hero-section">
        <h1>Document Categorization & Summarization</h1>
        <p className="subtitle">
          Upload your documents and let AI organize and summarize them for you
        </p>
      </div>
      
      <FileUpload />
      
      <div className="features">
        <div className="feature">
          <i className="fas fa-file-alt"></i>
          <h3>Multiple Formats</h3>
          <p>Support for PDFs, images, and text files</p>
        </div>
        <div className="feature">
          <i className="fas fa-brain"></i>
          <h3>AI-Powered</h3>
          <p>Advanced categorization using LayoutLMv3</p>
        </div>
        <div className="feature">
          <i className="fas fa-language"></i>
          <h3>Multilingual</h3>
          <p>Support for multiple languages</p>
        </div>
      </div>
    </div>
  );
};

export default Home;
