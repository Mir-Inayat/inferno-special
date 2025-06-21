import React, { useEffect } from 'react';
import { Link } from 'react-router-dom';
import './index.css';

function Index() {
  // Scroll-trigger logic
  useEffect(() => {
    const handleScroll = () => {
      const sections = document.querySelectorAll('section');
      const triggerHeight = window.innerHeight * 0.8;

      sections.forEach((section) => {
        const sectionTop = section.getBoundingClientRect().top;
        if (sectionTop < triggerHeight) {
          section.classList.add('visible');
        }
      });
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <div className="container">
      {/* Hero Section */}
      <section className="hero-section">
        <h1>Welcome to Inferno Intellect</h1>
        <p className="subtitle">
          Revolutionizing document processing with AI-powered automation and intelligent solutions
        </p>
      </section>

      {/* Why Us Section */}
      <section className="why-us">
        <h2>Why Choose Us?</h2>
        <div className="features-grid">
          <div className="feature">
            <h3>Multilingual Support</h3>
            <p>Breaking language barriers with AI-driven language support</p>
          </div>
          <div className="feature">
            <h3>AI Assistant</h3>
            <p>Voice-based interaction for seamless document management</p>
          </div>
          <div className="feature">
            <h3>Open-Source</h3>
            <p>Free, scalable, and cost-effective solutions</p>
          </div>
          <div className="feature">
            <h3>OCR Integration</h3>
            <p>Accurate text extraction from various document formats</p>
          </div>
        </div>
      </section>

      {/* Focus Areas Section */}
      <section className="focus-areas">
        <h2>Focus Areas</h2>
        <div className="focus-grid">
          <div className="focus-item">
            <h3>Document Upload</h3>
            <p>Drag-and-drop functionality for hassle-free uploads</p>
          </div>
          <div className="focus-item">
            <h3>Document Categorization</h3>
            <p>Robust AI for hierarchical document classification</p>
          </div>
          <div className="focus-item">
            <h3>Batch Processing</h3>
            <p>Efficient handling of large document volumes</p>
          </div>
          <div className="focus-item">
            <h3>Results Display</h3>
            <p>Confidence scores and analytics for decision-making</p>
          </div>
        </div>
      </section>

      {/* Call-to-Action Section */}
      <section className="cta">
        <h2>Get Started</h2>
        <p>
          Experience the future of document management with Inferno Intellect. Start processing your documents effortlessly today!
        </p>
        <Link to="/upload" className="cta-button">Upload Your Documents</Link>
      </section>
    </div>
  );
}

export default Index;
