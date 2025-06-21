import sqlite3

conn = sqlite3.connect('inferno_documents.db')
cursor = conn.cursor()

print("=== DOCUMENT FIELDS SCHEMA ===")
cursor.execute("PRAGMA table_info(document_fields)")
for row in cursor.fetchall():
    print(f"  {row[1]}: {row[2]}")

print("\n=== SAMPLE DOCUMENT FIELDS ===")
cursor.execute("SELECT * FROM document_fields LIMIT 5")
for row in cursor.fetchall():
    print(row)

conn.close()
