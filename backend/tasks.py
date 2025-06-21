from celery import Celery
from document_processor import DocumentProcessor

celery = Celery('tasks', broker='redis://localhost:6379/0')
processor = DocumentProcessor()

@celery.task
def process_document(file_path):
    return processor.process_document(file_path) 