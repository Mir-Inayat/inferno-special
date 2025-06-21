import sqlite3

def migrate_database():
    conn = sqlite3.connect('inferno_documents.db')
    cursor = conn.cursor()
    
    # Add missing columns if they don't exist
    columns_to_add = [
        'file_name TEXT',
        'user_id TEXT DEFAULT "system"',
        'primary_category TEXT',
        'person_name TEXT',
        'person_nationality TEXT',
        'person_gender TEXT',
        'person_date_of_birth TEXT',
        'person_profession TEXT',
        'document_number TEXT',
        'issue_date TEXT',
        'expiry_date TEXT',
        'issuing_authority TEXT',
        'place_of_issue TEXT',
        'additional_info TEXT',
        'extracted_data TEXT',
        'status TEXT DEFAULT "processed"',
        'needs_review INTEGER DEFAULT 0'
    ]
    
    for column_def in columns_to_add:
        col_name = column_def.split()[0]
        try:
            cursor.execute(f'ALTER TABLE documents ADD COLUMN {column_def}')
            print(f'Added {col_name} column')
        except sqlite3.OperationalError as e:
            if 'duplicate column name' in str(e):
                print(f'{col_name} column already exists')
            else:
                print(f'Error adding {col_name}: {e}')
    
    # Update existing records
    try:
        cursor.execute('UPDATE documents SET primary_category = document_type WHERE primary_category IS NULL')
        cursor.execute('UPDATE documents SET status = "processed" WHERE status IS NULL')
        # Extract filename from file_path for existing records
        cursor.execute('''
            UPDATE documents 
            SET file_name = CASE 
                WHEN file_path LIKE '%\\%' THEN SUBSTR(file_path, INSTR(file_path, '\', -1) + 1)
                WHEN file_path LIKE '%/%' THEN SUBSTR(file_path, INSTR(file_path, '/', -1) + 1)
                ELSE file_path
            END
            WHERE file_name IS NULL
        ''')
        print('Updated existing records')
    except Exception as e:
        print(f'Error updating records: {e}')
    
    conn.commit()
    conn.close()
    print('Database migration completed!')

if __name__ == '__main__':
    migrate_database()
