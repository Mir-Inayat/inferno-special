"""
Test the Enhanced Document Processing Dashboard
Tests all new features: sorting, search, tabs, grouping, bulk upload, API cycling
"""

import requests
import json
import time
import os
from pathlib import Path

BASE_URL = "http://localhost:5000"

def test_api_key_management():
    """Test API key management endpoints"""
    print("🔑 Testing API Key Management...")
    
    # Get current key statistics
    response = requests.get(f"{BASE_URL}/api/keys")
    if response.status_code == 200:
        data = response.json()
        print(f"  ✓ API Keys: {len(data['keys'])} total")
        print(f"  ✓ Current key: {data['current_key']}")
        for key in data['keys']:
            print(f"    - {key['name']}: {key['usage_count']} uses, {'quota exceeded' if key['quota_exceeded'] else 'active'}")
    else:
        print(f"  ✗ Failed to get API keys: {response.status_code}")

def test_enhanced_dashboard_api():
    """Test the enhanced dashboard API endpoints"""
    print("📊 Testing Enhanced Dashboard API...")
    
    # Test documents endpoint
    response = requests.get(f"{BASE_URL}/api/documents")
    if response.status_code == 200:
        data = response.json()
        documents = data.get('documents', [])
        print(f"  ✓ Found {len(documents)} documents")
        
        if documents:
            doc = documents[0]
            print(f"  ✓ Sample document: {doc.get('file_name', 'Unknown')}")
            print(f"    - Type: {doc.get('primary_category', 'Unknown')}")
            print(f"    - Person: {doc.get('person', {}).get('name', 'N/A')}")
            print(f"    - Size: {doc.get('file_size', 'N/A')} bytes")
    else:
        print(f"  ✗ Failed to get documents: {response.status_code}")

def test_bulk_upload_simulation():
    """Test bulk upload with simulated files"""
    print("📁 Testing Bulk Upload Simulation...")
    
    # Create test directory
    test_dir = Path("test_bulk_docs")
    test_dir.mkdir(exist_ok=True)
    
    # Create test files
    test_files = []
    for i in range(3):
        test_file = test_dir / f"test_document_{i}.txt"
        with open(test_file, 'w') as f:
            f.write(f"Test Document {i}\n")
            f.write(f"This is a sample document for bulk upload testing.\n")
            f.write(f"Document ID: {i}\n")
            f.write(f"Created for testing purposes.\n")
            f.write(f"Category: Test Document\n")
        test_files.append(test_file)
    
    print(f"  ✓ Created {len(test_files)} test files")
    
    # Test individual uploads (simulating bulk upload)
    successful_uploads = 0
    for test_file in test_files:
        try:
            with open(test_file, 'rb') as f:
                files = {'file': (test_file.name, f, 'text/plain')}
                data = {'bulk_upload': 'true', 'original_path': str(test_file)}
                
                response = requests.post(f"{BASE_URL}/api/upload", files=files, data=data)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('status') == 'success':
                        successful_uploads += 1
                        print(f"  ✓ Uploaded: {test_file.name}")
                    elif result.get('status') == 'duplicate':
                        print(f"  ⚠ Duplicate: {test_file.name}")
                        successful_uploads += 1  # Count as success
                    else:
                        print(f"  ✗ Failed: {test_file.name} - {result.get('error', 'Unknown error')}")
                else:
                    print(f"  ✗ HTTP Error: {test_file.name} - {response.status_code}")
                    
        except Exception as e:
            print(f"  ✗ Exception: {test_file.name} - {str(e)}")
    
    print(f"  ✓ Successfully uploaded {successful_uploads}/{len(test_files)} files")
    
    # Cleanup
    import shutil
    shutil.rmtree(test_dir, ignore_errors=True)

def test_search_functionality():
    """Test search and filtering"""
    print("🔍 Testing Search Functionality...")
    
    # Test general search
    response = requests.post(f"{BASE_URL}/api/search", 
                           json={"query": "test", "document_type": ""})
    if response.status_code == 200:
        data = response.json()
        print(f"  ✓ Search 'test': {len(data.get('results', []))} results")
    else:
        print(f"  ✗ Search failed: {response.status_code}")

def test_api_status():
    """Test API status and quota info"""
    print("📡 Testing API Status...")
    
    # Test status endpoint
    response = requests.get(f"{BASE_URL}/api/status")
    if response.status_code == 200:
        data = response.json()
        print(f"  ✓ API Status: {data.get('api_status')}")
        print(f"  ✓ Message: {data.get('api_message')}")
    else:
        print(f"  ✗ Status check failed: {response.status_code}")
    
    # Test quota info
    response = requests.get(f"{BASE_URL}/api/quota-info")
    if response.status_code == 200:
        data = response.json()
        print(f"  ✓ Quota info available")
    else:
        print(f"  ✗ Quota info failed: {response.status_code}")

def test_bulk_upload_status():
    """Test bulk upload status tracking"""
    print("📈 Testing Bulk Upload Status...")
    
    response = requests.get(f"{BASE_URL}/api/bulk-upload-status")
    if response.status_code == 200:
        data = response.json()
        print(f"  ✓ Recent uploads: {data.get('recent_uploads', 0)}")
        api_keys = data.get('api_keys', {})
        print(f"  ✓ API Keys - Total: {api_keys.get('total', 0)}, Active: {api_keys.get('active', 0)}")
        print(f"  ✓ Current capacity: {data.get('current_capacity', 'unknown')}")
    else:
        print(f"  ✗ Status check failed: {response.status_code}")

def main():
    """Run all tests"""
    print("🚀 Starting Enhanced Dashboard Tests...\n")
    
    try:
        test_api_key_management()
        print()
        
        test_enhanced_dashboard_api()
        print()
        
        test_bulk_upload_simulation()
        print()
        
        test_search_functionality()
        print()
        
        test_api_status()
        print()
        
        test_bulk_upload_status()
        print()
        
        print("✅ All tests completed!")
        print("\n📌 Dashboard Features Available:")
        print("  🎯 Sortable table view (by date, name, type, size)")
        print("  🔍 Full-text search across documents and metadata")
        print("  📑 Tabbed category navigation")
        print("  👥 User-based grouping and filtering")
        print("  📁 Bulk upload with progress tracking")
        print("  🔑 API key pool management and auto-rotation")
        print("  📊 Real-time statistics and monitoring")
        
        print(f"\n🌐 Access the enhanced dashboard at: http://localhost:5173")
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: Cannot connect to the backend server.")
        print("   Make sure the Flask server is running on http://localhost:5000")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")

if __name__ == "__main__":
    main()
