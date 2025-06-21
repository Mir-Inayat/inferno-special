import google.generativeai as genai
import os
import uuid
from datetime import datetime
import json
import sqlite3
from pathlib import Path
import base64
from typing import Dict, List, Optional, Tuple
import hashlib
import time
import random
from api_key_manager import APIKeyManager

class DocumentProcessor:
    def __init__(self, db_path: str = "inferno_documents.db"):
        # Initialize API key manager for robust key cycling
        self.api_manager = APIKeyManager(db_path)
        
        # Configure Gemini API with managed keys
        if not self.api_manager.configure_genai():
            raise Exception("No valid API keys available")
        
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.db_path = db_path
        self._init_database()
        
        # Rate limiting and retry configuration
        self.max_retries = 3
        self.retry_delay = 2  # seconds
        
        # Document type mappings and field specifications
        self.document_schemas = {
            "passport": {
                "required_fields": ["passport_number", "full_name", "nationality", "date_of_birth", "place_of_birth", "issue_date", "expiry_date", "issuing_authority"],
                "optional_fields": ["gender", "profession", "place_of_issue", "machine_readable_zone"]
            },
            "visa": {
                "required_fields": ["visa_number", "full_name", "passport_number", "visa_type", "issue_date", "expiry_date", "issuing_country"],
                "optional_fields": ["entries_allowed", "duration_of_stay", "sponsor_info", "purpose_of_visit"]
            },
            "emirates_id": {
                "required_fields": ["id_number", "full_name", "nationality", "date_of_birth", "gender", "issue_date", "expiry_date"],
                "optional_fields": ["place_of_birth", "mother_name", "card_delivery_date", "file_number"]
            },
            "driving_license": {
                "required_fields": ["license_number", "full_name", "date_of_birth", "issue_date", "expiry_date", "license_class"],
                "optional_fields": ["address", "restrictions", "endorsements", "issuing_authority", "blood_group"]
            },
            "residence_visa": {
                "required_fields": ["visa_number", "full_name", "passport_number", "sponsor_name", "issue_date", "expiry_date"],
                "optional_fields": ["profession", "salary", "sponsor_id", "entry_date", "visa_status"]
            },
            "work_permit": {
                "required_fields": ["permit_number", "full_name", "employer_name", "job_title", "issue_date", "expiry_date"],
                "optional_fields": ["salary", "work_location", "permit_type", "labor_card_number"]
            },
            "certificate": {
                "required_fields": ["certificate_number", "certificate_type", "issue_date", "issuing_authority"],
                "optional_fields": ["recipient_name", "expiry_date", "qualification_level", "institution_name", "grade_score"]
            },
            "inspection_certificate": {
                "required_fields": ["certificate_number", "equipment_type", "inspection_date", "inspector_name", "status"],
                "optional_fields": ["next_inspection_date", "serial_number", "manufacturer", "model", "location", "owner_contractor"]
            },
            "other": {
                "required_fields": ["document_title", "issue_date"],                "optional_fields": ["reference_number", "issuing_authority", "recipient_name", "expiry_date"]
            }
        }

    def _init_database(self):
        """Initialize SQLite database with comprehensive schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Main documents table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT UNIQUE NOT NULL,
                file_path TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                document_type TEXT NOT NULL,
                sub_category TEXT,
                processing_status TEXT DEFAULT 'processed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                file_size INTEGER,
                file_format TEXT,
                page_count INTEGER DEFAULT 1,
                raw_content TEXT,
                summary TEXT,
                notes TEXT
            )
        ''')
        
        # Persons table for linking documents to individuals
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS persons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_hash TEXT UNIQUE NOT NULL,
                primary_name TEXT NOT NULL,
                alternative_names TEXT,
                date_of_birth DATE,
                nationality TEXT,
                gender TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Document fields table for flexible field storage
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS document_fields (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT NOT NULL,
                field_name TEXT NOT NULL,
                field_value TEXT,
                field_type TEXT DEFAULT 'text',
                is_sensitive BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (document_id) REFERENCES documents (document_id),
                UNIQUE(document_id, field_name)
            )
        ''')
        
        # Person-Document relationships
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS person_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_hash TEXT NOT NULL,
                document_id TEXT NOT NULL,
                relationship_type TEXT DEFAULT 'owner',
                FOREIGN KEY (person_hash) REFERENCES persons (person_hash),
                FOREIGN KEY (document_id) REFERENCES documents (document_id),
                UNIQUE(person_hash, document_id)
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(document_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_created ON documents(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_fields_document ON document_fields(document_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_person_docs ON person_documents(person_hash)')
        
        conn.commit()
        conn.close()

    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file for duplicate detection"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def _create_person_hash(self, name: str, dob: str = None, nationality: str = None) -> str:
        """Create a consistent hash for person identification"""
        identifier = f"{name.lower().strip()}"
        if dob:
            identifier += f"_{dob}"
        if nationality:
            identifier += f"_{nationality.lower()}"
        return hashlib.md5(identifier.encode()).hexdigest()

    def _extract_document_info(self, file_path: str) -> Dict:
        """Extract comprehensive information using Gemini with enhanced prompting and retry logic"""
        max_retries = 3
        base_delay = 60  # Start with 60 seconds delay for rate limiting
        
        for attempt in range(max_retries):
            try:
                file = genai.upload_file(file_path)
                
                prompt = f"""
                Analyze this document thoroughly and extract ALL visible information. Return ONLY valid JSON format.

                Document types to consider: passport, visa, emirates_id, driving_license, residence_visa, work_permit, certificate, inspection_certificate, other

                Expected JSON structure:
                {{
                    "document_type": {{
                        "primary_category": "<one of the document types above>",
                        "sub_category": "<specific subtype if applicable>"
                    }},
                    "person_info": {{
                        "primary_name": "<full name as it appears>",
                        "alternative_names": ["<any other name variations>"],
                        "date_of_birth": "<YYYY-MM-DD format if found>",
                        "nationality": "<nationality if mentioned>",
                        "gender": "<M/F if mentioned>"
                    }},
                    "document_fields": {{
                        "passport_number": "<if passport>",
                        "visa_number": "<if visa>",
                        "id_number": "<if ID document>",
                        "license_number": "<if driving license>",
                        "certificate_number": "<if certificate>",
                        "issue_date": "<YYYY-MM-DD format>",
                        "expiry_date": "<YYYY-MM-DD format>",
                        "issuing_authority": "<issuing organization>",
                        "place_of_birth": "<if mentioned>",
                        "profession": "<if mentioned>",
                        "employer_name": "<if work document>",
                        "sponsor_name": "<if residence visa>",
                        "equipment_type": "<if inspection certificate>",
                        "serial_number": "<if equipment certificate>",
                        "inspection_status": "<if inspection certificate>",
                        "next_inspection_date": "<if applicable>",
                        "additional_fields": {{
                            "<field_name>": "<field_value>"
                        }}
                    }},
                    "extracted_text": "<all visible text content>",
                    "languages_detected": ["<list of languages>"],
                    "document_quality": "<excellent/good/fair/poor>",
                    "contains_sensitive_info": <true/false>
                }}

                Be thorough and extract every piece of information visible in the document.
                """

                response = self._make_api_call_with_retry(
                    "document_analysis",
                    self.model.generate_content,
                    [prompt, file]
                )
                response_text = response.text.strip()
                
                # Clean and parse JSON
                json_str = response_text.replace('```json', '').replace('```', '').strip()
                
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    # Try to extract JSON from response
                    import re
                    json_match = re.search(r'\{.*\}', json_str, re.DOTALL)
                    if json_match:
                        try:
                            return json.loads(json_match.group())
                        except json.JSONDecodeError:
                            pass
                    
                    # Fallback to basic extraction
                    return self._basic_extraction_fallback(file_path)

            except Exception as e:
                error_str = str(e)
                print(f"Extraction attempt {attempt + 1} failed: {error_str}")
                
                # Check if it's a rate limiting error
                if "429" in error_str or "RATE_LIMIT_EXCEEDED" in error_str or "Quota exceeded" in error_str:
                    if attempt < max_retries - 1:  # Don't wait on the last attempt
                        delay = base_delay * (2 ** attempt) + random.uniform(0, 10)  # Exponential backoff with jitter
                        print(f"Rate limit hit. Waiting {delay:.1f} seconds before retry...")
                        time.sleep(delay)
                        continue
                    else:
                        print("Rate limit exceeded. Using fallback extraction.")
                        return self._basic_extraction_fallback(file_path)
                else:
                    # For other errors, use fallback immediately
                    print(f"Non-rate-limit error: {error_str}")
                    return self._basic_extraction_fallback(file_path)
        
        # If all retries failed
        return self._basic_extraction_fallback(file_path)

    def _basic_extraction_fallback(self, file_path: str) -> Dict:
        """Fallback extraction method when AI processing fails"""
        # Extract basic info from filename and file properties
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        
        # Try to guess document type from filename
        doc_type = "other"
        if any(keyword in file_name.lower() for keyword in ['passport', 'pass']):
            doc_type = "passport"
        elif any(keyword in file_name.lower() for keyword in ['visa', 'entry']):
            doc_type = "visa"
        elif any(keyword in file_name.lower() for keyword in ['emirates', 'id', 'identity']):
            doc_type = "emirates_id"
        elif any(keyword in file_name.lower() for keyword in ['license', 'driving', 'dl']):
            doc_type = "driving_license"
        elif any(keyword in file_name.lower() for keyword in ['certificate', 'cert']):
            doc_type = "certificate"
        
        return {
            "document_type": {
                "primary_category": doc_type,
                "sub_category": "unknown"
            },
            "person_info": {
                "primary_name": "",
                "alternative_names": [],
                "date_of_birth": None,
                "nationality": None,
                "gender": None
            },
            "document_fields": {
                "file_name": file_name,
                "file_size_bytes": file_size
            },
            "extracted_text": f"Unable to process document: {file_name}. File size: {file_size} bytes. Please try again later or check API quota.",
            "languages_detected": [],
            "document_quality": "poor",
            "contains_sensitive_info": True,
            "processing_note": "Processed with fallback method due to API limitations"
        }

    def _store_document_in_db(self, document_data: Dict, file_path: str, file_hash: str) -> str:
        """Store document and related data in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            doc_info = document_data['classification']
            document_id = document_data['document_id']            # Insert main document record
            cursor.execute('''
                INSERT OR REPLACE INTO documents 
                (document_id, file_path, file_hash, document_type, sub_category,
                 file_size, file_format, raw_content, summary, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                document_id,
                file_path,
                file_hash,
                doc_info['document_type']['primary_category'],
                doc_info['document_type'].get('sub_category'),
                os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                Path(file_path).suffix[1:] if Path(file_path).suffix else 'unknown',
                doc_info.get('extracted_text', ''),
                document_data.get('summary', ''),
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            # Handle person information
            person_info = doc_info.get('person_info', {})
            if person_info.get('primary_name'):
                person_hash = self._create_person_hash(
                    person_info['primary_name'],
                    person_info.get('date_of_birth'),
                    person_info.get('nationality')
                )                # Insert or update person
                cursor.execute('''
                    INSERT OR REPLACE INTO persons 
                    (person_hash, primary_name, alternative_names, date_of_birth, nationality, gender, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    person_hash,
                    person_info['primary_name'],
                    json.dumps(person_info.get('alternative_names', [])),
                    person_info.get('date_of_birth'),
                    person_info.get('nationality'),
                    person_info.get('gender'),
                    datetime.now().isoformat()
                ))                # Link person to document
                cursor.execute('''
                    INSERT OR REPLACE INTO person_documents (person_hash, document_id)
                    VALUES (?, ?)
                ''', (person_hash, document_id))
              # Store document fields
            document_fields = doc_info.get('document_fields', {})
            for field_name, field_value in document_fields.items():
                if field_value and field_name != 'additional_fields':
                    # Determine if field is sensitive
                    sensitive_fields = ['passport_number', 'id_number', 'visa_number', 'license_number', 
                                      'date_of_birth', 'serial_number']
                    is_sensitive = field_name in sensitive_fields
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO document_fields 
                        (document_id, field_name, field_value, is_sensitive)
                        VALUES (?, ?, ?, ?)
                    ''', (document_id, field_name, str(field_value), is_sensitive))
            
            # Handle additional fields
            additional_fields = document_fields.get('additional_fields', {})
            for field_name, field_value in additional_fields.items():
                if field_value:                    cursor.execute('''
                        INSERT OR REPLACE INTO document_fields 
                        (document_id, field_name, field_value, is_sensitive)
                        VALUES (?, ?, ?, ?)
                    ''', (document_id, field_name, str(field_value), False))
            
            conn.commit()
            return document_id
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def process_document(self, file_path: str) -> Dict:
        """Main document processing method"""
        try:
            if not os.path.exists(file_path):
                return {"status": "error", "error": "File not found"}
              # Calculate file hash for duplicate detection
            file_hash = self._calculate_file_hash(file_path)
            
            # Check if document already exists
            is_duplicate, duplicate_info = self._is_duplicate(file_hash)
            if is_duplicate:
                return {
                    "status": "duplicate",
                    "message": "Document already processed",
                    "error": "This document has already been uploaded and processed",
                    "duplicate_details": {
                        "original_document_id": duplicate_info.get("document_id"),
                        "original_upload_date": duplicate_info.get("upload_date"),
                        "document_type": duplicate_info.get("document_type"),
                        "message": "A document with identical content was previously uploaded"
                    }
                }
            
            # Extract document information
            doc_info = self._extract_document_info(file_path)
            
            # Generate document ID
            document_id = f"DOC{uuid.uuid4().hex[:8].upper()}"
            
            # Prepare document data structure
            document_data = {
                "status": "success",
                "document_id": document_id,
                "classification": doc_info,
                "metadata": {
                    "date_received": datetime.now().strftime("%Y-%m-%d"),
                    "processing_timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "file_type": Path(file_path).suffix[1:],
                    "file_size": os.path.getsize(file_path),
                    "file_hash": file_hash
                },
                "summary": self._generate_summary(doc_info)
            }
            
            # Store in database
            stored_doc_id = self._store_document_in_db(document_data, file_path, file_hash)
            document_data["database_id"] = stored_doc_id
            
            return document_data
            
        except Exception as e:
            print(f"Processing error: {str(e)}")
            return {"status": "error", "error": str(e)}

    def _is_duplicate(self, file_hash: str) -> tuple[bool, dict]:
        """Check if document with same hash already exists and return details"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT document_id, file_path, created_at, document_type 
            FROM documents 
            WHERE file_hash = ? 
            LIMIT 1
        """, (file_hash,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return True, {
                "document_id": result[0],
                "original_file_path": result[1],
                "upload_date": result[2],
                "document_type": result[3]
            }
        return False, {}

    def _generate_summary(self, doc_info: Dict) -> str:
        """Generate a human-readable summary of the document"""
        doc_type = doc_info['document_type']['primary_category']
        person_name = doc_info.get('person_info', {}).get('primary_name', 'Unknown')
        
        if doc_type == 'passport':
            return f"Passport document for {person_name}"
        elif doc_type == 'visa':
            return f"Visa document for {person_name}"
        elif doc_type == 'emirates_id':
            return f"Emirates ID for {person_name}"
        elif doc_type == 'driving_license':
            return f"Driving license for {person_name}"
        elif doc_type == 'residence_visa':
            return f"Residence visa for {person_name}"
        elif doc_type == 'certificate':
            return f"Certificate document for {person_name}"
        else:
            return f"{doc_type.replace('_', ' ').title()} document"

    def batch_process_documents(self, folder_path: str, file_extensions: List[str] = None) -> Dict:
        """Process multiple documents in a folder"""
        if file_extensions is None:
            file_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.bmp']
        
        results = {
            "processed": [],
            "errors": [],
            "duplicates": [],
            "summary": {}
        }
        
        folder_path = Path(folder_path)
        if not folder_path.exists():
            return {"status": "error", "error": "Folder not found"}
        
        # Find all matching files
        files_to_process = []
        for ext in file_extensions:
            files_to_process.extend(folder_path.glob(f"*{ext}"))
            files_to_process.extend(folder_path.glob(f"*{ext.upper()}"))
        
        print(f"Found {len(files_to_process)} files to process")
        
        for file_path in files_to_process:
            print(f"Processing: {file_path.name}")
            result = self.process_document(str(file_path))
            
            if result["status"] == "success":
                results["processed"].append(result)
            elif result["status"] == "duplicate":
                results["duplicates"].append(str(file_path))
            else:
                results["errors"].append({"file": str(file_path), "error": result.get("error")})
        
        # Generate summary statistics
        results["summary"] = {
            "total_files": len(files_to_process),
            "processed_successfully": len(results["processed"]),
            "duplicates_found": len(results["duplicates"]),
            "errors_encountered": len(results["errors"]),
            "processing_date": datetime.now().isoformat()
        }
        
        return results

    def get_documents_by_person(self, person_name: str) -> List[Dict]:
        """Retrieve all documents for a specific person"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT d.*, p.primary_name, p.nationality, p.date_of_birth
            FROM documents d
            JOIN person_documents pd ON d.document_id = pd.document_id
            JOIN persons p ON pd.person_hash = p.person_hash
            WHERE p.primary_name LIKE ?
            ORDER BY d.created_at DESC
        ''', (f"%{person_name}%",))
        
        documents = []
        for row in cursor.fetchall():
            doc = dict(zip([col[0] for col in cursor.description], row))
            
            # Get document fields
            cursor.execute('''
                SELECT field_name, field_value, is_sensitive
                FROM document_fields
                WHERE document_id = ?
            ''', (doc['document_id'],))
            
            fields = {}
            for field_row in cursor.fetchall():
                field_name, field_value, is_sensitive = field_row
                if is_sensitive:
                    fields[field_name] = self._mask_sensitive_data(field_value)
                else:
                    fields[field_name] = field_value
            
            doc['fields'] = fields
            documents.append(doc)
        
        conn.close()
        return documents

    def get_documents_by_type(self, document_type: str) -> List[Dict]:
        """Retrieve all documents of a specific type"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT d.*, COUNT(df.field_name) as field_count
            FROM documents d
            LEFT JOIN document_fields df ON d.document_id = df.document_id
            WHERE d.document_type = ?
            GROUP BY d.document_id
            ORDER BY d.created_at DESC
        ''', (document_type,))
        
        documents = []
        for row in cursor.fetchall():
            documents.append(dict(zip([col[0] for col in cursor.description], row)))
        
        conn.close()
        return documents

    def _mask_sensitive_data(self, value: str) -> str:
        """Mask sensitive information for display"""
        if not value or len(value) < 4:
            return "****"
        return f"****{value[-4:]}"

    def get_database_statistics(self) -> Dict:
        """Get comprehensive database statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        # Document type distribution
        cursor.execute('''
            SELECT document_type, COUNT(*) as count
            FROM documents
            GROUP BY document_type
            ORDER BY count DESC
        ''')
        stats['document_types'] = dict(cursor.fetchall())
        
        # Person count
        cursor.execute('SELECT COUNT(*) FROM persons')
        stats['total_persons'] = cursor.fetchone()[0]
        
        # Total documents
        cursor.execute('SELECT COUNT(*) FROM documents')
        stats['total_documents'] = cursor.fetchone()[0]
        
        # Documents per person
        cursor.execute('''
            SELECT p.primary_name, COUNT(pd.document_id) as doc_count
            FROM persons p
            LEFT JOIN person_documents pd ON p.person_hash = pd.person_hash
            GROUP BY p.person_hash
            ORDER BY doc_count DESC
            LIMIT 10
        ''')
        stats['top_persons_by_documents'] = dict(cursor.fetchall())
        
        # Recent processing activity
        cursor.execute('''
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM documents
            WHERE created_at >= date('now', '-30 days')
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        ''')
        stats['recent_activity'] = dict(cursor.fetchall())
        
        conn.close()
        return stats

    def _make_api_call_with_retry(self, operation: str, func, *args, **kwargs):
        """Make API call with automatic retry and key switching"""
        current_key = self.api_manager.get_current_key()
        
        for attempt in range(self.max_retries):
            try:
                result = func(*args, **kwargs)
                
                # Log successful usage
                self.api_manager.log_api_usage(
                    current_key, operation, True
                )
                
                return result
                
            except Exception as e:
                error_msg = str(e)
                print(f"API call attempt {attempt + 1} failed: {error_msg}")
                
                # Check if it's a quota/rate limit error
                if any(keyword in error_msg.lower() for keyword in 
                       ["quota", "limit", "429", "rate_limit_exceeded"]):
                    self.api_manager.mark_key_quota_exceeded(current_key)
                    self.api_manager.log_api_usage(
                        current_key, operation, False, error_msg
                    )
                    
                    # Try to switch to next key
                    if self.api_manager.switch_to_next_key():
                        current_key = self.api_manager.get_current_key()
                        self.model = genai.GenerativeModel('gemini-1.5-flash')
                        print(f"Switched to new API key")
                        continue
                    else:
                        print("All API keys exhausted")
                        raise Exception("All API keys exhausted")
                
                # For other errors, log and retry with delay
                self.api_manager.log_api_usage(
                    current_key, operation, False, error_msg
                )
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    raise e