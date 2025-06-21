import sqlite3

conn = sqlite3.connect('inferno_documents.db')
cursor = conn.cursor()

print("=== DOCUMENTS WITH ID/PROFESSION FIELDS ===")
cursor.execute("""
    SELECT d.document_id, df.field_name, df.field_value 
    FROM documents d 
    JOIN document_fields df ON d.id = df.document_id 
    WHERE df.field_name IN ('id_number', 'profession')
    LIMIT 10
""")

for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]} = {row[2]}")

conn.close()
