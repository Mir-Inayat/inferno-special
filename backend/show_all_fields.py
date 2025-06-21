import sqlite3

conn = sqlite3.connect('inferno_documents.db')
cursor = conn.cursor()

print("=== ALL DOCUMENT FIELDS BY DOCUMENT ===")
cursor.execute("""
    SELECT d.document_id, d.document_type, d.summary,
           df.field_name, df.field_value, df.is_sensitive
    FROM documents d
    LEFT JOIN document_fields df ON d.document_id = df.document_id 
    WHERE d.document_id IN ('DOC4C9F707D', 'DOC7D463AD6', 'DOCDE82B32F')
    ORDER BY d.document_id, df.field_name
""")

current_doc = None
for row in cursor.fetchall():
    if row[0] != current_doc:
        current_doc = row[0]
        print(f"\n=== {row[0]} ({row[1]}) ===")
        print(f"Summary: {row[2]}")
        print("Fields:")
    
    if row[3]:  # If field_name exists
        sensitive = "🔒" if row[5] else "📄"
        print(f"  {sensitive} {row[3]}: {row[4]}")

conn.close()
