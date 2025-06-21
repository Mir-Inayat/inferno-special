import sqlite3

conn = sqlite3.connect('inferno_documents.db')
cursor = conn.cursor()

print("=== DOCUMENTS TABLE SCHEMA ===")
cursor.execute("PRAGMA table_info(documents)")
for row in cursor.fetchall():
    print(f"  {row[1]}: {row[2]}")

print("\n=== SAMPLE DOCUMENT DATA ===")
cursor.execute("SELECT * FROM documents LIMIT 1")
row = cursor.fetchone()
if row:
    cursor.execute("PRAGMA table_info(documents)")
    cols = [col[1] for col in cursor.fetchall()]
    print("Sample data:")
    for i, col in enumerate(cols):
        if i < len(row):
            print(f"  {col}: {row[i]}")

conn.close()
