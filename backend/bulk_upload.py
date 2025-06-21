"""
Bulk Upload Utility for Document Processing
Handles large-scale document ingestion with progress tracking
"""

import os
import asyncio
import aiohttp
import aiofiles
from pathlib import Path
import time
import json
from typing import List, Dict, Optional
import mimetypes

class BulkUploadManager:
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.upload_endpoint = f"{base_url}/api/upload"
        self.supported_extensions = {'.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.txt'}
        self.max_concurrent = 5  # Limit concurrent uploads
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        
    def scan_directory(self, directory_path: str, recursive: bool = True) -> List[str]:
        """Scan directory for supported document files"""
        directory = Path(directory_path)
        files = []
        
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory_path}")
        
        pattern = "**/*" if recursive else "*"
        
        for file_path in directory.glob(pattern):
            if file_path.is_file() and file_path.suffix.lower() in self.supported_extensions:
                # Check file size
                if file_path.stat().st_size <= self.max_file_size:
                    files.append(str(file_path))
                else:
                    print(f"Skipping large file: {file_path} ({file_path.stat().st_size / 1024 / 1024:.1f}MB)")
        
        return files
    
    async def upload_single_file(self, session: aiohttp.ClientSession, file_path: str, 
                                 semaphore: asyncio.Semaphore) -> Dict:
        """Upload a single file asynchronously"""
        async with semaphore:
            try:
                file_path_obj = Path(file_path)
                
                # Prepare form data
                async with aiofiles.open(file_path, 'rb') as file:
                    file_content = await file.read()
                
                # Determine MIME type
                mime_type, _ = mimetypes.guess_type(file_path)
                if not mime_type:
                    mime_type = 'application/octet-stream'
                
                # Create form data
                data = aiohttp.FormData()
                data.add_field('file', 
                              file_content,
                              filename=file_path_obj.name,
                              content_type=mime_type)
                
                # Add metadata
                data.add_field('bulk_upload', 'true')
                data.add_field('original_path', str(file_path))
                
                # Upload with timeout
                timeout = aiohttp.ClientTimeout(total=300)  # 5 minutes
                async with session.post(self.upload_endpoint, data=data, timeout=timeout) as response:
                    result_text = await response.text()
                    
                    if response.status == 200:
                        try:
                            result = json.loads(result_text)
                            return {
                                'file_path': file_path,
                                'status': 'success',
                                'document_id': result.get('document_id'),
                                'message': result.get('message', 'Upload successful')
                            }
                        except json.JSONDecodeError:
                            return {
                                'file_path': file_path,
                                'status': 'success',
                                'message': 'Upload successful (no JSON response)'
                            }
                    else:
                        return {
                            'file_path': file_path,
                            'status': 'error',
                            'error': f"HTTP {response.status}: {result_text}"
                        }
            
            except asyncio.TimeoutError:
                return {
                    'file_path': file_path,
                    'status': 'error',
                    'error': 'Upload timeout (file too large or server slow)'
                }
            except Exception as e:
                return {
                    'file_path': file_path,
                    'status': 'error',
                    'error': str(e)
                }
    
    async def bulk_upload_async(self, file_paths: List[str], 
                               progress_callback: Optional[callable] = None) -> Dict:
        """Upload multiple files asynchronously"""
        start_time = time.time()
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        # Set up HTTP session with connection pooling
        connector = aiohttp.TCPConnector(limit=20, limit_per_host=10)
        timeout = aiohttp.ClientTimeout(total=None)  # No overall timeout
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # Create upload tasks
            tasks = [
                self.upload_single_file(session, file_path, semaphore)
                for file_path in file_paths
            ]
            
            # Process uploads with progress tracking
            results = []
            completed = 0
            
            for coro in asyncio.as_completed(tasks):
                result = await coro
                results.append(result)
                completed += 1
                
                if progress_callback:
                    progress_callback(completed, len(file_paths), result)
        
        # Compile statistics
        end_time = time.time()
        successful = [r for r in results if r['status'] == 'success']
        failed = [r for r in results if r['status'] == 'error']
        
        return {
            'total_files': len(file_paths),
            'successful': len(successful),
            'failed': len(failed),
            'duration': end_time - start_time,
            'results': results,
            'success_rate': len(successful) / len(file_paths) * 100 if file_paths else 0
        }
    
    def bulk_upload(self, directory_path: str, recursive: bool = True, 
                   progress_callback: Optional[callable] = None) -> Dict:
        """Main bulk upload function"""
        # Scan for files
        print(f"Scanning directory: {directory_path}")
        file_paths = self.scan_directory(directory_path, recursive)
        
        if not file_paths:
            return {
                'error': 'No supported files found in directory',
                'total_files': 0,
                'successful': 0,
                'failed': 0
            }
        
        print(f"Found {len(file_paths)} files to upload")
        
        # Start async upload
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.bulk_upload_async(file_paths, progress_callback)
            )
        finally:
            loop.close()


def progress_printer(completed: int, total: int, result: Dict):
    """Simple progress callback for console output"""
    status_symbol = "✓" if result['status'] == 'success' else "✗"
    file_name = Path(result['file_path']).name
    
    print(f"[{completed}/{total}] {status_symbol} {file_name}")
    
    if result['status'] == 'error':
        print(f"    Error: {result['error']}")


def simulate_user_uploads(num_users: int = 5, files_per_user: int = 10):
    """Simulate multiple users uploading documents simultaneously"""
    import random
    import threading
    
    # Sample document directories (you would replace with real paths)
    sample_directories = [
        "sample_docs/user1",
        "sample_docs/user2",
        "sample_docs/user3",
        "sample_docs/user4",
        "sample_docs/user5"
    ]
    
    def user_upload_session(user_id: int):
        """Simulate a user upload session"""
        print(f"User {user_id} starting upload session...")
        
        # Create some dummy files for testing if directories don't exist
        user_dir = f"temp_user_{user_id}_docs"
        os.makedirs(user_dir, exist_ok=True)
        
        # Generate dummy files for testing
        for i in range(files_per_user):
            dummy_file = Path(user_dir) / f"document_{i}.txt"
            with open(dummy_file, 'w') as f:
                f.write(f"This is a test document {i} for user {user_id}\n")
                f.write(f"Created at: {time.ctime()}\n")
                f.write("Sample content for document processing...")
        
        # Upload files
        manager = BulkUploadManager()
        result = manager.bulk_upload(user_dir, progress_callback=None)
        
        print(f"User {user_id} completed: {result['successful']}/{result['total_files']} successful")
        
        # Cleanup
        import shutil
        shutil.rmtree(user_dir, ignore_errors=True)
    
    # Start user sessions in parallel
    threads = []
    for user_id in range(1, num_users + 1):
        thread = threading.Thread(target=user_upload_session, args=(user_id,))
        threads.append(thread)
        thread.start()
        
        # Stagger starts slightly
        time.sleep(random.uniform(0.5, 2.0))
    
    # Wait for all to complete
    for thread in threads:
        thread.join()
    
    print(f"Simulation complete: {num_users} users, {files_per_user} files each")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python bulk_upload.py <directory_path>         # Upload files from directory")
        print("  python bulk_upload.py --simulate               # Simulate multi-user uploads")
        print("  python bulk_upload.py --test                   # Test with small batch")
        sys.exit(1)
    
    if sys.argv[1] == "--simulate":
        print("Starting multi-user upload simulation...")
        simulate_user_uploads(num_users=3, files_per_user=5)
    
    elif sys.argv[1] == "--test":
        print("Creating test files...")
        test_dir = "test_bulk_upload"
        os.makedirs(test_dir, exist_ok=True)
        
        # Create test files
        for i in range(5):
            test_file = Path(test_dir) / f"test_doc_{i}.txt"
            with open(test_file, 'w') as f:
                f.write(f"Test document {i}\nCreated for bulk upload testing\n")
        
        print(f"Starting bulk upload from {test_dir}...")
        manager = BulkUploadManager()
        result = manager.bulk_upload(test_dir, progress_callback=progress_printer)
        
        print(f"\nUpload completed:")
        print(f"  Total files: {result['total_files']}")
        print(f"  Successful: {result['successful']}")
        print(f"  Failed: {result['failed']}")
        print(f"  Success rate: {result['success_rate']:.1f}%")
        print(f"  Duration: {result['duration']:.2f} seconds")
        
        # Cleanup
        import shutil
        shutil.rmtree(test_dir, ignore_errors=True)
    
    else:
        directory = sys.argv[1]
        recursive = "--no-recursive" not in sys.argv
        
        print(f"Starting bulk upload from: {directory}")
        print(f"Recursive: {recursive}")
        
        manager = BulkUploadManager()
        result = manager.bulk_upload(
            directory, 
            recursive=recursive, 
            progress_callback=progress_printer
        )
        
        print(f"\nBulk upload completed:")
        print(f"  Total files: {result['total_files']}")
        print(f"  Successful: {result['successful']}")
        print(f"  Failed: {result['failed']}")
        print(f"  Success rate: {result['success_rate']:.1f}%")
        print(f"  Duration: {result['duration']:.2f} seconds")
        
        if result['failed'] > 0:
            print(f"\nFailed uploads:")
            for failed_result in [r for r in result['results'] if r['status'] == 'error']:
                print(f"  {failed_result['file_path']}: {failed_result['error']}")
