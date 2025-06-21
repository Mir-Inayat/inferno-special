from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Document, Person
import os
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from document_processor import DocumentProcessor
from deep_translator import GoogleTranslator
import google.generativeai as genai
from upload_manager import UploadManager, DocumentEditManager, assess_document_quality

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["http://localhost:5173", "http://localhost:5174"]}})

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'tiff', 'txt'}
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # Increased to 50MB max file size

# Initialize document processor with new database
processor = DocumentProcessor("inferno_documents.db")
upload_manager = UploadManager(app, processor, app.config['UPLOAD_FOLDER'])
edit_manager = DocumentEditManager()

# Make sure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Database setup
DATABASE_URL = "sqlite:///./inferno_documents.db"
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_person_for_document(document_id):
    """Get comprehensive person and document information from DocumentProcessor DB"""
    try:
        import sqlite3
        conn = sqlite3.connect('inferno_documents.db')
        cursor = conn.cursor()
        
        # Get person info via person_documents relationship
        cursor.execute("""
            SELECT p.primary_name, p.nationality, p.gender, p.date_of_birth
            FROM person_documents pd
            JOIN persons p ON pd.person_hash = p.person_hash
            WHERE pd.document_id = ?
        """, (document_id,))
        
        person_result = cursor.fetchone()
        
        # Get all document fields
        cursor.execute("""
            SELECT field_name, field_value, is_sensitive
            FROM document_fields df
            JOIN documents d ON df.document_id = d.document_id
            WHERE d.document_id = ?
            ORDER BY field_name
        """, (document_id,))
        
        fields = cursor.fetchall()
        conn.close()
        
        # Process fields into organized categories
        field_dict = {field[0]: field[1] for field in fields}
        sensitive_fields = {field[0]: field[2] for field in fields}
        
        # Organize data into logical sections
        personal_info = {
            "name": person_result[0] if person_result else field_dict.get("primary_name", "N/A"),
            "nationality": person_result[1] if person_result else field_dict.get("nationality", "N/A"),
            "gender": person_result[2] if person_result else field_dict.get("gender", "N/A"),
            "date_of_birth": person_result[3] if person_result else field_dict.get("date_of_birth", "N/A"),
            "profession": field_dict.get("profession") or field_dict.get("Profession") or "N/A"
        }
        
        # Document identifiers
        document_info = {
            "id_number": field_dict.get("id_number", "N/A"),
            "passport_number": field_dict.get("passport_number", "N/A"),
            "visa_number": field_dict.get("visa_number", "N/A"),
            "license_number": field_dict.get("license_number", "N/A"),
            "file_number": field_dict.get("File") or field_dict.get("file_number", "N/A")
        }
        
        # Dates and validity
        dates_info = {
            "issue_date": field_dict.get("issue_date", "N/A"),
            "expiry_date": field_dict.get("expiry_date", "N/A"),
            "issuing_authority": field_dict.get("issuing_authority", "N/A"),
            "place_of_issue": field_dict.get("Place of Issue") or field_dict.get("place_of_issue", "N/A")
        }
        
        # Work/Employment info
        employment_info = {
            "employer_name": field_dict.get("employer_name", "N/A"),
            "sponsor_name": field_dict.get("sponsor_name", "N/A"),
            "job_title": field_dict.get("job_title", "N/A")
        }
        
        # Additional fields for special document types
        additional_info = {}
        for field_name, field_value in field_dict.items():
            if field_name not in [
                "primary_name", "nationality", "gender", "date_of_birth", "profession",
                "id_number", "passport_number", "visa_number", "license_number", "File", "file_number",
                "issue_date", "expiry_date", "issuing_authority", "Place of Issue", "place_of_issue",
                "employer_name", "sponsor_name", "job_title", "file_name", "file_size_bytes"
            ]:
                additional_info[field_name] = field_value
        
        return {
            "personal": personal_info,
            "document": document_info,
            "dates": dates_info,
            "employment": employment_info,
            "additional": additional_info,
            # Backward compatibility
            "name": personal_info["name"],
            "government_id": document_info["id_number"],
            "nationality": personal_info["nationality"],
            "gender": personal_info["gender"],
            "profession": personal_info["profession"]
        }
            
    except Exception as e:
        print(f"Error getting person for document {document_id}: {e}")
        return {
            "personal": {"name": "N/A", "nationality": "N/A", "gender": "N/A", "date_of_birth": "N/A", "profession": "N/A"},
            "document": {"id_number": "N/A", "passport_number": "N/A", "visa_number": "N/A", "license_number": "N/A", "file_number": "N/A"},
            "dates": {"issue_date": "N/A", "expiry_date": "N/A", "issuing_authority": "N/A", "place_of_issue": "N/A"},
            "employment": {"employer_name": "N/A", "sponsor_name": "N/A", "job_title": "N/A"},
            "additional": {},
            "name": "N/A", "government_id": "N/A", "nationality": "N/A", "gender": "N/A", "profession": "N/A"
        }

@app.route('/api/documents', methods=['GET'])
def get_documents():
    session = Session()
    try:
        documents = session.query(Document).all()
        return jsonify({
            "status": "success",            "documents": [{
                "id": doc.id,
                "file_name": doc.file_path.split('\\')[-1] if doc.file_path else f"Document {doc.document_id}",
                "primary_category": doc.document_type,
                "sub_category": doc.sub_category,
                "summary": doc.summary,
                "file_size": doc.file_size,
                "file_format": doc.file_format,
                "processing_status": doc.processing_status,
                "upload_date": doc.created_at.isoformat() if doc.created_at else None,
                "person": get_person_for_document(doc.document_id) if doc.document_id else None
            } for doc in documents]
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        session.close()

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'files[]' not in request.files:
        print("No files provided in request")
        return jsonify({"error": "No files provided"}), 400

    files = request.files.getlist('files[]')
    session = Session()
    
    try:
        results = []
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                print(f"Processing file: {filename}")
                file.save(file_path)
                  # Process document
                print("Starting document processing...")
                doc_info = processor.process_document(file_path)
                print(f"Document processing result: {doc_info}")
                
                if doc_info.get('status') == 'error':
                    raise Exception(doc_info.get('error', 'Unknown processing error'))
                
                if doc_info.get('status') == 'duplicate':
                    # Handle duplicate documents gracefully
                    results.append({
                        "status": "duplicate",
                        "filename": filename,
                        "message": "Document already uploaded",
                        "error": doc_info.get('error', 'Duplicate document detected'),
                        "duplicate_details": doc_info.get('duplicate_details', {})
                    })
                    continue                # Document was successfully processed by DocumentProcessor
                # which already handled database storage
                results.append(doc_info)
                print(f"Successfully processed file: {filename}")
          # No need for session.commit() as DocumentProcessor handles its own database
        return jsonify({"status": "success", "results": results})
    
    except Exception as e:
        print(f"Error during processing: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/download/<int:doc_id>')
def download_document(doc_id):
    session = Session()
    try:
        document = session.query(Document).get(doc_id)
        if document and os.path.exists(document.file_path):
            return send_file(document.file_path)
        return jsonify({"error": "Document not found"}), 404
    finally:
        session.close()

@app.route('/api/translate', methods=['POST'])
def translate_text():
    try:
        data = request.get_json()
        text = data.get('text', '')
        target_language = data.get('target_language', 'en')
        
        if target_language == 'en':
            return jsonify({"translatedText": text})
        
        # Use the translator from document_processor
        from deep_translator import GoogleTranslator
        translator = GoogleTranslator(source='auto', target=target_language)
        translated = translator.translate(text)
        
        return jsonify({"translatedText": translated})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/batch-process', methods=['POST'])
def batch_process():
    try:
        data = request.get_json()
        folder_path = data.get('folder_path')
        
        if not folder_path:
            return jsonify({"error": "Folder path is required"}), 400
        
        # Use the enhanced batch processing
        results = processor.batch_process_documents(folder_path)
        return jsonify(results)
    
    except Exception as e:
        print(f"Batch processing error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/documents/by-person/<person_name>', methods=['GET'])
def get_documents_by_person(person_name):
    try:
        documents = processor.get_documents_by_person(person_name)
        return jsonify({
            "status": "success",
            "person_name": person_name,
            "documents": documents
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/documents/by-type/<document_type>', methods=['GET'])
def get_documents_by_type(document_type):
    try:
        documents = processor.get_documents_by_type(document_type)
        return jsonify({
            "status": "success",
            "document_type": document_type,
            "documents": documents
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    try:
        stats = processor.get_database_statistics()
        return jsonify({
            "status": "success",
            "statistics": stats
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/search', methods=['POST'])
def search_documents():
    try:
        data = request.get_json()
        query = data.get('query', '')
        doc_type = data.get('document_type', '')
        
        session = Session()
        documents_query = session.query(Document)
        
        if doc_type:
            documents_query = documents_query.filter(Document.primary_category == doc_type)
        
        if query:
            documents_query = documents_query.filter(
                Document.file_name.contains(query) |
                Document.summary.contains(query) |
                Document.processed_text.contains(query)
            )
        
        documents = documents_query.all()
        
        return jsonify({
            "status": "success",
            "query": query,
            "document_type": doc_type,
            "results": [{
                "id": doc.id,
                "file_name": doc.file_name,
                "primary_category": doc.primary_category,
                "sub_category": doc.sub_category,
                "summary": doc.summary,
                "upload_date": doc.upload_date.isoformat() if doc.upload_date else None
            } for doc in documents]
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()

@app.route('/api/status', methods=['GET'])
def get_api_status():
    """Check API and system status"""
    try:
        # Test a simple Gemini API call
        test_prompt = "Hello, respond with just 'OK'"
        response = processor.model.generate_content(test_prompt)
        api_status = "OK"
        api_message = "Gemini API is operational"
    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "RATE_LIMIT_EXCEEDED" in error_str:
            api_status = "RATE_LIMITED"
            api_message = "API rate limit exceeded. Please wait before uploading more documents."
        else:
            api_status = "ERROR"
            api_message = f"API error: {error_str}"

    return jsonify({
        "status": "success",
        "api_status": api_status,
        "api_message": api_message,
        "database": "inferno_documents.db",
        "fallback_processing": "Available",
        "max_file_size": "50MB"
    })

@app.route('/api/quota-info', methods=['GET'])
def get_quota_info():
    """Provide information about API quota and alternatives"""
    return jsonify({
        "status": "info",
        "quota_info": {
            "current_limit": "Free tier: Limited requests per minute",
            "upgrade_options": [
                "Request quota increase from Google Cloud Console",
                "Upgrade to paid tier for higher limits",
                "Use batch processing with delays"
            ],
            "alternatives": [
                "Process documents one at a time with delays",
                "Use fallback processing (basic extraction)",
                "Schedule processing during off-peak hours"
            ]
        },
        "fallback_processing": {
            "description": "When API quota is exceeded, the system uses basic file analysis",
            "capabilities": [
                "Document type detection from filename",
                "File size and format analysis", 
                "Basic metadata extraction"
            ]
        }
    })

@app.errorhandler(413)
def too_large(e):
    return jsonify({
        "error": "File is too large. Maximum allowed size is 50MB.",
        "max_size": "50MB"
    }), 413

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500

@app.route('/api/profiles', methods=['GET', 'POST'])
def handle_profiles():
    if request.method == 'GET':
        # Return user profile information
        return jsonify({
            "status": "success",
            "profile": {
                "name": "User",
                "email": "user@example.com",
                "documents_count": get_all_documents()
            }
        })
    elif request.method == 'POST':
        # Create/update profile
        return jsonify({"status": "success", "message": "Profile updated"})

@app.route('/api/profiles/my', methods=['PUT'])
def update_my_profile():
    # Update current user's profile
    return jsonify({"status": "success", "message": "Profile updated successfully"})

def get_all_documents():
    """Helper function to get document count"""
    try:
        import sqlite3
        conn = sqlite3.connect('inferno_documents.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM documents")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except:
        return 0

# API Key Management Endpoints
@app.route('/api/keys', methods=['GET'])
def get_api_keys():
    """Get API key statistics"""
    try:
        from api_key_manager import APIKeyManager
        manager = APIKeyManager()
        stats = manager.get_key_statistics()
        return jsonify({
            "status": "success",
            "keys": stats,
            "current_key": manager.get_current_key()[:20] + "..." if manager.get_current_key() else None
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/keys', methods=['POST'])
def add_api_key():
    """Add a new API key"""
    try:
        data = request.get_json()
        api_key = data.get('api_key')
        name = data.get('name')
        notes = data.get('notes', '')
        
        if not api_key or not name:
            return jsonify({"error": "API key and name are required"}), 400
        
        from api_key_manager import APIKeyManager
        manager = APIKeyManager()
        key_id = manager.add_api_key(api_key, name, notes=notes)
        
        if key_id:
            return jsonify({
                "status": "success",
                "message": f"API key '{name}' added successfully",
                "key_id": key_id
            })
        else:
            return jsonify({"error": "API key already exists"}), 400
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/keys/switch', methods=['POST'])
def switch_api_key():
    """Manually switch to next API key"""
    try:
        from api_key_manager import APIKeyManager
        manager = APIKeyManager()
        success = manager.switch_to_next_key()
        
        if success:
            # Update processor's model
            processor.model = genai.GenerativeModel('gemini-1.5-flash')
            return jsonify({
                "status": "success",
                "message": "Switched to next API key",
                "current_key": manager.get_current_key()[:20] + "..."
            })
        else:
            return jsonify({"error": "Failed to switch API key"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Enhanced Upload Endpoint with Bulk Support
@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Enhanced upload endpoint supporting single files and bulk uploads"""
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed"}), 400

    try:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Save file
        file.save(file_path)
        
        # Check if this is part of a bulk upload
        is_bulk = request.form.get('bulk_upload') == 'true'
        original_path = request.form.get('original_path', '')
        
        print(f"Processing {'bulk ' if is_bulk else ''}upload: {filename}")
        
        # Process document
        doc_info = processor.process_document(file_path)
        
        if doc_info.get('status') == 'error':
            # For bulk uploads, don't fail completely on individual errors
            if is_bulk:
                return jsonify({
                    "status": "error",
                    "filename": filename,
                    "original_path": original_path,
                    "error": doc_info.get('error', 'Processing failed'),
                    "bulk_upload": True
                }), 200  # Return 200 for bulk processing
            else:
                return jsonify({"error": doc_info.get('error', 'Processing failed')}), 500
        
        if doc_info.get('status') == 'duplicate':
            return jsonify({
                "status": "duplicate",
                "filename": filename,
                "original_path": original_path,
                "message": "Document already uploaded",
                "duplicate_details": doc_info.get('duplicate_details', {}),
                "bulk_upload": is_bulk
            })
        
        # Success response
        response_data = {
            "status": "success",
            "filename": filename,
            "document_id": doc_info.get('document_id'),
            "message": "File uploaded and processed successfully",
            "document_type": doc_info.get('document_type'),
            "bulk_upload": is_bulk
        }
        
        if original_path:
            response_data["original_path"] = original_path
            
        return jsonify(response_data)
        
    except Exception as e:
        error_msg = str(e)
        print(f"Upload error: {error_msg}")
        
        # Handle rate limiting gracefully for bulk uploads
        if is_bulk and any(keyword in error_msg.lower() for keyword in ["quota", "limit", "429"]):
            return jsonify({
                "status": "rate_limited",
                "filename": filename,
                "original_path": original_path,
                "error": "API rate limit reached. File will be processed later.",
                "bulk_upload": True
            }), 200
        
        return jsonify({"error": error_msg}), 500

@app.route('/api/bulk-upload-status', methods=['GET'])
def bulk_upload_status():
    """Get bulk upload progress and statistics"""
    try:
        from api_key_manager import APIKeyManager
        manager = APIKeyManager()
        key_stats = manager.get_key_statistics()
        
        # Get recent upload statistics from database
        session = Session()
        recent_docs = session.query(Document).filter(
            Document.created_at >= datetime.now() - timedelta(hours=1)
        ).all()
        
        return jsonify({
            "status": "success",
            "recent_uploads": len(recent_docs),
            "api_keys": {
                "total": len(key_stats),
                "active": len([k for k in key_stats if k['active']]),
                "quota_exceeded": len([k for k in key_stats if k['quota_exceeded']])
            },
            "current_capacity": "high" if len([k for k in key_stats if k['active'] and not k['quota_exceeded']]) > 0 else "limited"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()

# Import additional dependencies
from datetime import datetime, timedelta
from upload_manager import UploadManager, DocumentEditManager, assess_document_quality

# Initialize upload manager
upload_manager = UploadManager(app, processor, app.config['UPLOAD_FOLDER'])
edit_manager = DocumentEditManager()

# Enhanced Upload Route with Folder Support
@app.route('/upload', methods=['GET', 'POST'])
def upload_route():
    """Enhanced upload route supporting files, folders, and ZIP archives"""
    if request.method == 'GET':
        # Return upload page or status
        return jsonify({
            "status": "ready",
            "supported_formats": [".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".txt", ".docx", ".doc"],
            "max_file_size": "50MB",
            "max_bulk_size": "500MB",
            "features": ["single_file", "multiple_files", "zip_archive", "folder_structure"]
        })
    
    try:
        results = []
        
        # Handle different upload types
        if 'file' in request.files:
            # Single file upload
            file = request.files['file']
            if file and file.filename:
                if file.filename.endswith('.zip'):
                    # ZIP archive upload
                    result = upload_manager.process_zip_upload(file)
                    return jsonify(result)
                else:
                    # Regular file upload
                    if allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        file.save(file_path)
                        
                        doc_info = processor.process_document(file_path)
                        
                        # Assess quality and determine if review is needed
                        quality_assessment = assess_document_quality(doc_info)
                        doc_info['quality_assessment'] = quality_assessment
                        
                        return jsonify(doc_info)
                    else:
                        return jsonify({"error": "File type not allowed"}), 400
        
        elif 'files[]' in request.files:
            # Multiple files upload
            files = request.files.getlist('files[]')
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    
                    doc_info = processor.process_document(file_path)
                    quality_assessment = assess_document_quality(doc_info)
                    doc_info['quality_assessment'] = quality_assessment
                    
                    results.append(doc_info)
            
            return jsonify({
                "status": "success",
                "total": len(results),
                "successful": len([r for r in results if r.get('status') == 'success']),
                "results": results
            })
        
        else:
            return jsonify({"error": "No files provided"}), 400
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Document Editing Routes
@app.route('/api/documents/<document_id>/edit', methods=['GET'])
def get_document_for_edit(document_id):
    """Get document data for editing"""
    try:
        document_data = edit_manager.get_document_for_editing(document_id)
        return jsonify(document_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/documents/<document_id>/edit', methods=['PUT'])
def update_document(document_id):
    """Update document fields"""
    try:
        updates = request.get_json()
        result = edit_manager.update_document(document_id, updates)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/documents/<document_id>', methods=['DELETE'])
def delete_document(document_id):
    """Delete document"""
    try:
        result = edit_manager.delete_document(document_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/documents/needs-review', methods=['GET'])
def get_documents_needing_review():
    """Get documents that need user review"""
    try:
        documents = edit_manager.get_documents_needing_review()
        return jsonify({
            "status": "success",
            "count": len(documents),
            "documents": documents
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/documents/<document_id>/quality', methods=['GET'])
def assess_document_quality_route(document_id):
    """Assess document quality"""
    try:
        document_data = edit_manager.get_document_for_editing(document_id)
        if 'error' in document_data:
            return jsonify(document_data), 404
        
        quality_assessment = assess_document_quality(document_data)
        return jsonify(quality_assessment)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Import reporting modules
from reporting import ReportGenerator, AdvancedAnalytics
from flask import send_file
import sqlite3
import pandas as pd

# Initialize reporting
report_generator = ReportGenerator()
analytics = AdvancedAnalytics()

# Reporting Routes
@app.route('/api/reports/excel', methods=['GET'])
def download_excel_report():
    """Generate and download Excel report"""
    try:
        excel_buffer = report_generator.generate_excel_report()
        
        return send_file(
            excel_buffer,
            as_attachment=True,
            download_name=f'document_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/reports/pdf', methods=['GET'])
def download_pdf_report():
    """Generate and download PDF report with visualizations"""
    try:
        pdf_buffer = report_generator.generate_pdf_report()
        
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=f'document_analytics_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf',
            mimetype='application/pdf'
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/analytics/dashboard', methods=['GET'])
def get_dashboard_analytics():
    """Get analytics data for interactive dashboard"""
    try:
        dashboard_data = report_generator.generate_interactive_dashboard_data()
        return jsonify({
            "status": "success",
            "data": dashboard_data
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/analytics/insights', methods=['GET'])
def get_processing_insights():
    """Get processing insights and suggestions"""
    try:
        insights = analytics.get_processing_insights()
        suggestions = analytics.suggest_improvements()
        
        return jsonify({
            "status": "success",
            "insights": insights,
            "suggestions": suggestions
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/analytics/quality-metrics', methods=['GET'])
def get_quality_metrics():
    """Get document quality metrics"""
    try:
        conn = sqlite3.connect('inferno_documents.db')
        
        # Quality metrics query
        quality_query = """
            SELECT d.document_type,
                   COUNT(*) as total_docs,
                   AVG(CASE WHEN d.processing_status = 'processed' THEN 1.0 ELSE 0.0 END) * 100 as success_rate,
                   AVG(
                       CASE WHEN df.total_fields > 0 
                       THEN ((df.total_fields - df.empty_fields) * 100.0 / df.total_fields)
                       ELSE 0 END
                   ) as avg_completion_rate
            FROM documents d
            LEFT JOIN (
                SELECT document_id,
                       COUNT(*) as total_fields,
                       SUM(CASE WHEN field_value IN ('N/A', '', 'Unknown', 'None') THEN 1 ELSE 0 END) as empty_fields
                FROM document_fields
                GROUP BY document_id
            ) df ON d.document_id = df.document_id
            GROUP BY d.document_type
            ORDER BY total_docs DESC
        """
        
        quality_df = pd.read_sql_query(quality_query, conn)
        conn.close()
        
        metrics = {
            'by_document_type': quality_df.to_dict('records'),
            'overall_metrics': {
                'total_documents': int(quality_df['total_docs'].sum()),
                'average_success_rate': float(quality_df['success_rate'].mean()),
                'average_completion_rate': float(quality_df['avg_completion_rate'].mean())
            }
        }
        
        return jsonify({
            "status": "success",
            "quality_metrics": metrics
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
