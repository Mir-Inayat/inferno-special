from document_processor import DocumentProcessor

def test_document_processing():
    # Initialize the processor
    processor = DocumentProcessor()
    
    # Provide a valid file path to a PDF or image
    file_path = r"C:\Users\inayat\Downloads\WhatsApp Image 2025-01-01 at 5.07.44 PM.jpeg"  # Replace with actual file path
    
    # Process the document
    result = processor.process_document(file_path)
    
    # Print the result
    print(result)

if __name__ == "__main__":
    test_document_processing()
