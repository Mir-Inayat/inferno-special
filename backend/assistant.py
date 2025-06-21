import google.generativeai as genai
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Document, Person, Category, Base
import json

class DocumentAssistant:
    def __init__(self):
        # Configure Gemini API
        genai.configure(api_key="AIzaSyBIKuGKwYEmo41cOTXPjKGIu3ue7ELwPus")
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Configure database connection
        self.engine = create_engine('sqlite:///documents.db')
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        # Initialize conversation history
        self.chat = self.model.start_chat(history=[])

    def _get_document_context(self):
        """Retrieve relevant document information from database"""
        context = {
            'documents': [],
            'persons': [],
            'categories': []
        }
        
        # Get all documents with their related information
        documents = self.session.query(Document).all()
        for doc in documents:
            doc_info = {
                'id': doc.id,
                'primary_category': doc.primary_category,
                'sub_category': doc.sub_category,
                'summary': doc.summary,
                'extracted_fields': doc.extracted_fields,
                'file_type': doc.file_type,
                'upload_date': str(doc.upload_date) if doc.upload_date else None
            }
            context['documents'].append(doc_info)
            
            if doc.person:
                person_info = {
                    'id': doc.person.id,
                    'name': doc.person.name,
                    'email': doc.person.email
                }
                if person_info not in context['persons']:
                    context['persons'].append(person_info)

        return context

    def ask_question(self, question):
        """Process user question and provide an answer based on document context"""
        try:
            # Get context from database
            context = self._get_document_context()
            
            # Construct prompt with context
            prompt = f"""
            Given the following database context:
            {json.dumps(context, indent=2)}

            Please answer this question: {question}

            Rules:
            1. Only use information from the provided context
            2. If you can't find relevant information, say so
            3. Keep responses concise and focused
            4. Don't reveal sensitive information like government IDs
            5. Cite specific documents when possible
            """

            # Get response from Gemini
            response = self.chat.send_message(prompt)
            return response.text

        except Exception as e:
            return f"I apologize, but I encountered an error: {str(e)}"

    def get_document_summary(self, document_id):
        """Get a specific document's summary"""
        try:
            document = self.session.query(Document).filter(Document.id == document_id).first()
            if document:
                return document.summary
            return "Document not found"
        except Exception as e:
            return f"Error retrieving document summary: {str(e)}"

    def search_documents(self, query):
        """Search through documents based on content or metadata"""
        try:
            # Get context
            context = self._get_document_context()
            
            prompt = f"""
            Given these documents:
            {json.dumps(context['documents'], indent=2)}

            Find documents relevant to this search query: "{query}"
            Return only the document IDs and a brief explanation of why they match.
            """

            response = self.model.generate_content(prompt)
            return response.text

        except Exception as e:
            return f"Search error: {str(e)}"

    def close(self):
        """Close the database session"""
        self.session.close()

def main():
    assistant = DocumentAssistant()
    print("Document Assistant initialized. Type 'quit' to exit.")
    
    try:
        while True:
            question = input("\nWhat would you like to know about the documents? ")
            if question.lower() == 'quit':
                break
            
            answer = assistant.ask_question(question)
            print("\nAssistant:", answer)
    
    finally:
        assistant.close()

if __name__ == "__main__":
    main() 