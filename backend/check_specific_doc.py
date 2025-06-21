import sqlite3

conn = sqlite3.connect('inferno_documents.db')
cursor = conn.cursor()

print("=== DOCUMENT FIELDS FOR DOC4C9F707D ===")
cursor.execute("""
    SELECT d.document_id, d.document_type, d.summary,
           df.field_name, df.field_value, df.is_sensitive
    FROM documents d
    LEFT JOIN document_fields df ON d.id = df.document_id 
    WHERE d.document_id = 'DOC4C9F707D'
    ORDER BY df.field_name
""")

for row in cursor.fetchall():
    print(f"Field: {row[3]} = {row[4]} (sensitive: {row[5]})")

conn.close()
