"""
Enhanced Upload Management System
Supports single files, bulk uploads, and folder-level processing
"""

import os
import shutil
import zipfile
import tempfile
from pathlib import Path
from flask import request, jsonify
from werkzeug.utils import secure_filename
import mimetypes
from datetime import datetime
import json

class UploadManager:
    def __init__(self, app, processor, upload_folder):
        self.app = app
        self.processor = processor
        self.upload_folder = upload_folder
        self.supported_extensions = {'.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.txt', '.docx', '.doc'}
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        self.max_total_size = 500 * 1024 * 1024  # 500MB for bulk uploads
        
    def extract_metadata_from_path(self, file_path: str) -> dict:
        """Extract metadata from file path structure"""
        path_obj = Path(file_path)
        metadata = {
            'original_folder': str(path_obj.parent.name),
            'folder_hierarchy': list(path_obj.parts[:-1]),
            'file_extension': path_obj.suffix.lower(),
            'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
            'creation_time': datetime.fromtimestamp(os.path.getctime(file_path)).isoformat() if os.path.exists(file_path) else None,
            'modification_time': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat() if os.path.exists(file_path) else None
        }
        
        # Try to infer document type from folder structure
        folder_names = [part.lower() for part in path_obj.parts]
        
        # Common folder patterns
        if any(keyword in ' '.join(folder_names) for keyword in ['passport', 'passports']):
            metadata['suggested_type'] = 'passport'
        elif any(keyword in ' '.join(folder_names) for keyword in ['visa', 'visas']):
            metadata['suggested_type'] = 'visa'
        elif any(keyword in ' '.join(folder_names) for keyword in ['license', 'driving', 'dl']):
            metadata['suggested_type'] = 'driving_license'
        elif any(keyword in ' '.join(folder_names) for keyword in ['id', 'emirates', 'national']):
            metadata['suggested_type'] = 'emirates_id'
        elif any(keyword in ' '.join(folder_names) for keyword in ['certificate', 'cert', 'diploma']):
            metadata['suggested_type'] = 'certificate'
        else:
            metadata['suggested_type'] = 'other'
            
        return metadata
    
    def process_zip_upload(self, zip_file) -> dict:
        """Process uploaded ZIP file containing documents"""
        results = []
        total_size = 0
        
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Extract ZIP file
                with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                # Recursively find all supported files
                extracted_files = []
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if Path(file_path).suffix.lower() in self.supported_extensions:
                            file_size = os.path.getsize(file_path)
                            if file_size <= self.max_file_size:
                                total_size += file_size
                                if total_size <= self.max_total_size:
                                    extracted_files.append(file_path)
                                else:
                                    break
                
                # Process each file
                for file_path in extracted_files:
                    try:
                        result = self.process_single_file_from_path(file_path, is_bulk=True)
                        results.append(result)
                    except Exception as e:
                        results.append({
                            'file_path': file_path,
                            'status': 'error',
                            'error': str(e)
                        })
                
                return {
                    'status': 'success',
                    'total_files': len(extracted_files),
                    'processed': len([r for r in results if r.get('status') == 'success']),
                    'failed': len([r for r in results if r.get('status') == 'error']),
                    'results': results
                }
                
            except zipfile.BadZipFile:
                return {'status': 'error', 'error': 'Invalid ZIP file'}
            except Exception as e:
                return {'status': 'error', 'error': str(e)}
    
    def process_single_file_from_path(self, file_path: str, is_bulk: bool = False) -> dict:
        """Process a single file from a file path"""
        try:
            # Extract metadata from path
            metadata = self.extract_metadata_from_path(file_path)
            
            # Copy file to upload folder
            filename = secure_filename(Path(file_path).name)
            destination_path = os.path.join(self.upload_folder, filename)
            
            # Handle filename conflicts
            counter = 1
            base_name, ext = os.path.splitext(filename)
            while os.path.exists(destination_path):
                filename = f"{base_name}_{counter}{ext}"
                destination_path = os.path.join(self.upload_folder, filename)
                counter += 1
            
            shutil.copy2(file_path, destination_path)
            
            # Process document with enhanced metadata
            doc_info = self.processor.process_document(destination_path, additional_metadata=metadata)
            
            if doc_info.get('status') == 'success':
                doc_info.update({
                    'filename': filename,
                    'original_path': file_path,
                    'folder_metadata': metadata,
                    'bulk_upload': is_bulk
                })
            
            return doc_info
            
        except Exception as e:
            return {
                'file_path': file_path,
                'status': 'error',
                'error': str(e)
            }


class DocumentEditManager:
    """Handles document editing and review functionality"""
    
    def __init__(self, db_path: str = "inferno_documents.db"):
        self.db_path = db_path
    
    def get_document_for_editing(self, document_id: str) -> dict:
        """Get document with all editable fields"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get document info
            cursor.execute("""
                SELECT document_id, file_path, document_type, sub_category, 
                       processing_status, summary, notes, created_at
                FROM documents WHERE document_id = ?
            """, (document_id,))
            
            doc_result = cursor.fetchone()
            if not doc_result:
                return {'error': 'Document not found'}
            
            # Get person info
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
                FROM document_fields
                WHERE document_id = ?
                ORDER BY field_name
            """, (document_id,))
            
            fields = cursor.fetchall()
            
            # Organize editable data
            document_data = {
                'document_id': doc_result[0],
                'file_path': doc_result[1],
                'document_type': doc_result[2],
                'sub_category': doc_result[3],
                'processing_status': doc_result[4],
                'summary': doc_result[5],
                'notes': doc_result[6],
                'created_at': doc_result[7],
                'person': {
                    'name': person_result[0] if person_result else '',
                    'nationality': person_result[1] if person_result else '',
                    'gender': person_result[2] if person_result else '',
                    'date_of_birth': person_result[3] if person_result else ''
                },
                'fields': {field[0]: field[1] for field in fields},
                'sensitive_fields': {field[0]: field[2] for field in fields}
            }
            
            return document_data
            
        finally:
            conn.close()
    
    def update_document(self, document_id: str, updates: dict) -> dict:
        """Update document fields"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Update document basic info
            if 'document_type' in updates:
                cursor.execute("""
                    UPDATE documents 
                    SET document_type = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE document_id = ?
                """, (updates['document_type'], document_id))
            
            if 'sub_category' in updates:
                cursor.execute("""
                    UPDATE documents 
                    SET sub_category = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE document_id = ?
                """, (updates['sub_category'], document_id))
            
            if 'summary' in updates:
                cursor.execute("""
                    UPDATE documents 
                    SET summary = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE document_id = ?
                """, (updates['summary'], document_id))
            
            if 'notes' in updates:
                cursor.execute("""
                    UPDATE documents 
                    SET notes = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE document_id = ?
                """, (updates['notes'], document_id))
            
            # Update person information
            if 'person' in updates:
                person_updates = updates['person']
                
                # Get person hash for this document
                cursor.execute("""
                    SELECT person_hash FROM person_documents WHERE document_id = ?
                """, (document_id,))
                
                person_result = cursor.fetchone()
                if person_result:
                    person_hash = person_result[0]
                    
                    # Update person fields
                    person_fields = ['primary_name', 'nationality', 'gender', 'date_of_birth']
                    for field in person_fields:
                        if field in person_updates:
                            cursor.execute(f"""
                                UPDATE persons 
                                SET {field} = ?, updated_at = CURRENT_TIMESTAMP
                                WHERE person_hash = ?
                            """, (person_updates[field], person_hash))
            
            # Update document fields
            if 'fields' in updates:
                field_updates = updates['fields']
                
                for field_name, field_value in field_updates.items():
                    # Check if field exists
                    cursor.execute("""
                        SELECT id FROM document_fields 
                        WHERE document_id = ? AND field_name = ?
                    """, (document_id, field_name))
                    
                    if cursor.fetchone():
                        # Update existing field
                        cursor.execute("""
                            UPDATE document_fields 
                            SET field_value = ?
                            WHERE document_id = ? AND field_name = ?
                        """, (field_value, document_id, field_name))
                    else:
                        # Insert new field
                        cursor.execute("""
                            INSERT INTO document_fields (document_id, field_name, field_value)
                            VALUES (?, ?, ?)
                        """, (document_id, field_name, field_value))
            
            # Mark as user-reviewed
            cursor.execute("""
                UPDATE documents 
                SET processing_status = 'user_reviewed', updated_at = CURRENT_TIMESTAMP
                WHERE document_id = ?
            """, (document_id,))
            
            conn.commit()
            return {'status': 'success', 'message': 'Document updated successfully'}
            
        except Exception as e:
            conn.rollback()
            return {'status': 'error', 'error': str(e)}
        finally:
            conn.close()
    
    def delete_document(self, document_id: str) -> dict:
        """Delete document and associated data"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get file path for cleanup
            cursor.execute("SELECT file_path FROM documents WHERE document_id = ?", (document_id,))
            result = cursor.fetchone()
            file_path = result[0] if result else None
            
            # Delete from all related tables
            cursor.execute("DELETE FROM document_fields WHERE document_id = ?", (document_id,))
            cursor.execute("DELETE FROM person_documents WHERE document_id = ?", (document_id,))
            cursor.execute("DELETE FROM documents WHERE document_id = ?", (document_id,))
            
            # Delete physical file
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
            
            conn.commit()
            return {'status': 'success', 'message': 'Document deleted successfully'}
            
        except Exception as e:
            conn.rollback()
            return {'status': 'error', 'error': str(e)}
        finally:
            conn.close()
    
    def get_documents_needing_review(self) -> list:
        """Get documents that need user review (many N/A fields)"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT d.document_id, d.file_path, d.document_type, d.summary,
                       COUNT(df.field_name) as total_fields,
                       SUM(CASE WHEN df.field_value IN ('N/A', '', 'Unknown', 'None') THEN 1 ELSE 0 END) as na_fields
                FROM documents d
                LEFT JOIN document_fields df ON d.document_id = df.document_id
                WHERE d.processing_status = 'processed'
                GROUP BY d.document_id
                HAVING na_fields > 3 OR (na_fields * 1.0 / total_fields) > 0.5
                ORDER BY na_fields DESC
            """)
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'document_id': row[0],
                    'file_path': row[1],
                    'document_type': row[2],
                    'summary': row[3],
                    'total_fields': row[4],
                    'na_fields': row[5],
                    'completion_rate': ((row[4] - row[5]) / row[4] * 100) if row[4] > 0 else 0
                })
            
            return results
            
        finally:
            conn.close()


# Quality Assessment Function
def assess_document_quality(document_data: dict) -> dict:
    """Assess document processing quality and suggest review"""
    quality_score = 100
    issues = []
    
    # Check for N/A values in important fields
    important_fields = ['primary_name', 'date_of_birth', 'nationality', 'id_number', 
                       'passport_number', 'issue_date', 'expiry_date']
    
    na_count = 0
    for field in important_fields:
        if document_data.get('fields', {}).get(field) in ['N/A', '', 'Unknown', 'None', None]:
            na_count += 1
    
    if na_count > 0:
        quality_score -= (na_count * 15)
        issues.append(f"{na_count} important fields are missing or marked as N/A")
    
    # Check summary quality
    summary = document_data.get('summary', '')
    if not summary or len(summary) < 20:
        quality_score -= 20
        issues.append("Document summary is too brief or missing")
    
    # Check for generic or incomplete names
    name = document_data.get('person', {}).get('name', '')
    if name in ['None', 'N/A', '', 'Unknown'] or len(name) < 3:
        quality_score -= 25
        issues.append("Person name is missing or incomplete")
    
    # Determine review recommendation
    needs_review = quality_score < 70 or len(issues) > 2
    
    return {
        'quality_score': max(0, quality_score),
        'needs_review': needs_review,
        'issues': issues,
        'recommendation': 'Requires manual review' if needs_review else 'Good quality'
    }
