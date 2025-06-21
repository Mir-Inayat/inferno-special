import sqlite3
import os

os.chdir('backend')
conn = sqlite3.connect('inferno_documents.db')
cursor = conn.cursor()

print("=== DATABASE SCHEMA ===")
cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
tables = [row[0] for row in cursor.fetchall()]
print('Tables:', tables)

for table in ['documents', 'persons', 'document_fields']:
    print(f"\n=== {table.upper()} TABLE ===")
    cursor.execute(f'PRAGMA table_info({table})')
    for row in cursor.fetchall():
        print(f"  {row[1]} ({row[2]})")

# Let's also check some sample data
print("\n=== SAMPLE PERSONS DATA ===")
cursor.execute('SELECT * FROM persons LIMIT 3')
columns = [description[0] for description in cursor.description]
print("Columns:", columns)
for row in cursor.fetchall():
    print(row)

print("\n=== SAMPLE DOCUMENT_FIELDS DATA ===")
cursor.execute('SELECT document_id, field_name, field_value FROM document_fields LIMIT 15')
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]} = {row[2]}")

conn.close()
