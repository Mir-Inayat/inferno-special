import google.generativeai as genai

# Configure the API key
genai.configure(api_key="AIzaSyBIKuGKwYEmo41cOTXPjKGIu3ue7ELwPus")

# Initialize the model
gemini_model = genai.GenerativeModel('gemini-pro')

# Generate content
response = gemini_model.generate_content("Write a short story about a cat.")
print(response.text)
