# Automated Document Categorization & Summarization

## Overview
This repository contains the implementation of an AI-powered tool designed for the **Appian AI Application Challenge**. The project aims to automate the categorization and summarization of unstructured financial documents, streamlining document management for financial institutions. 

---

## Key Features
1. **Hierarchical Document Categorization**:
   - Associates documents with the correct individual using identifiers like name, government ID, and email.
   - Categorizes by document type (e.g., applications, identity documents, receipts).

2. **Support for Multiple Formats**:
   - Processes PDFs, images, and text files seamlessly.

3. **AI-Powered Automation**:
   - Utilizes Hugging Face's **LayoutLMv3** model for document classification and summarization.

4. **Multilingual Support**:
   - Handles documents in multiple languages.

5. **Batch Processing Capability**:
   - Integrates **Redis** and **Celery** for handling large batches of documents efficiently.

6. **Drag-and-Drop Functionality**:
   - Simplifies document upload through an intuitive drag-and-drop interface.

7. **Voice-Enabled AI Assistant**:
   - Communicates key document details interactively using voice-based AI.

8. **Deployment**:
   - Backend deployed on **Streamlit Community Cloud** for free and scalable hosting.
   - Frontend built with **React** for a dynamic and responsive user interface.

---

## Technology Stack
- **Frontend:** React for a dynamic and interactive user interface.
- **Backend:** Hugging Face Transformers for text classification and summarization.
- **OCR:** Tesseract for text extraction from PDFs.
- **Batch Processing:** Redis and Celery.
- **Deployment:**
  - Frontend: Deployed on platforms like Vercel or Netlify.
  - Backend: Deployed on Streamlit Community Cloud.

---

## Installation
### Prerequisites
- Node.js
- Python 3.8+
- npm or yarn

1.  bashCopy codecd backendpip install -r requirements.txt
    
2.  bashCopy codecd ../frontendnpm install
    
3.  Run the application:
    
    *   bashCopy codecd ../backendstreamlit run app.py
        
    *   bashCopy codecd ../frontendnpm start


Basic UI
-----
![image](https://github.com/user-attachments/assets/b7697b6d-0839-4574-b1cf-381e0239ec08)
![image](https://github.com/user-attachments/assets/4cf2581c-8197-497a-8dab-932f9d50d233)


Usage
-----

*   Drag and drop documents into the upload area on the React frontend.
    
*   View categorized results with confidence scores.
    
*   Interact with the AI assistant for voice-based document insights.


File Structure
``` bash
.
├── backend/              # Backend application
│   ├── app.py           # Main application script
│   ├── requirements.txt # Dependencies
│   ├── models/          # Pretrained models
│   └── templates/       # HTML templates
├── frontend/             # React frontend
│   ├── src/             # Source code
│   ├── public/          # Public assets
│   ├── package.json     # Frontend dependencies
│   └── README.md        # Frontend documentation
└── README.md             # Project documentation
```

Future Enhancements
-------------------

*   Add user correction feedback.
    
*   Integrate cloud storage for document management.
    
*   Advanced compliance checks for financial regulations.
  
*   Add ai assistant and multilingual support
    

Contributors
------------

Mir Inayat Ahmed
Mohammed Muqeet Us Salam
Abdullah Shaikh
Armaan Rashid Pathan
