import sqlite3

conn = sqlite3.connect('inferno_documents.db')
cursor = conn.cursor()

print("=== PERSON DATA FOR DOCUMENTS ===")
cursor.execute("""
    SELECT d.document_id, d.document_type, d.summary,
           p.primary_name, 
           GROUP_CONCAT(df.field_name || ': ' || df.field_value, ', ') as fields
    FROM documents d
    LEFT JOIN person_documents pd ON d.id = pd.document_id 
    LEFT JOIN persons p ON pd.person_id = p.id
    LEFT JOIN document_fields df ON d.id = df.document_id 
    WHERE df.field_name IN ('id_number', 'passport_number', 'visa_number')
    GROUP BY d.document_id, p.primary_name
    LIMIT 5
""")

for row in cursor.fetchall():
    print(f"Doc: {row[0]}, Type: {row[1]}")
    print(f"  Person: {row[3]}")
    print(f"  Fields: {row[4]}")
    print(f"  Summary: {row[2]}")
    print()

conn.close()
