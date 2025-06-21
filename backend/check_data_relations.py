import sqlite3

conn = sqlite3.connect('inferno_documents.db')
cursor = conn.cursor()

print("=== PERSON DOCUMENTS ===")
cursor.execute("SELECT * FROM person_documents LIMIT 5")
for row in cursor.fetchall():
    print(row)

print("\n=== DOCUMENT FIELDS (ID Numbers) ===")
cursor.execute("SELECT df.document_id, df.field_name, df.extracted_value FROM document_fields df WHERE df.field_name IN ('id_number', 'passport_number') LIMIT 5")
for row in cursor.fetchall():
    print(row)

print("\n=== DOCUMENTS WITH PERSON INFO ===")
cursor.execute("""
    SELECT d.document_id, d.document_type, d.summary, 
           GROUP_CONCAT(df.field_name || ': ' || df.extracted_value, ', ') as fields
    FROM documents d
    LEFT JOIN document_fields df ON d.id = df.document_id 
    WHERE df.field_name IN ('id_number', 'passport_number', 'primary_name')
    GROUP BY d.document_id
    LIMIT 3
""")
for row in cursor.fetchall():
    print(row)

conn.close()
