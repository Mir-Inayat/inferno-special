import sqlite3

conn = sqlite3.connect('inferno_documents.db')
cursor = conn.cursor()

print("=== DOCUMENT FIELDS COUNT ===")
cursor.execute("SELECT COUNT(*) FROM document_fields")
count = cursor.fetchone()[0]
print(f"Total document fields: {count}")

print("\n=== SAMPLE DOCUMENT FIELDS ===")
cursor.execute("SELECT * FROM document_fields LIMIT 10")
for row in cursor.fetchall():
    print(row)

conn.close()
