import sqlite3

# Check the actual database schema
conn = sqlite3.connect('inferno_documents.db')
cursor = conn.cursor()

print("=== PERSONS TABLE SCHEMA ===")
cursor.execute("PRAGMA table_info(persons)")
for row in cursor.fetchall():
    print(f"Column: {row[1]}, Type: {row[2]}")

print("\n=== ALL TABLES ===")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
for table in tables:
    print(f"Table: {table[0]}")

conn.close()
