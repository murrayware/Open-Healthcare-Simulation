"""
Migration script to add hospital_id column to the compare table.
Run this once to update existing database.
"""
from sqlalchemy import text
from database.users_table import engine

def migrate_add_hospital_id():
    """Add hospital_id column to compare table if it doesn't exist."""
    
    # Check if column already exists
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(compare)"))
        columns = [row[1] for row in result]
        
        if 'hospital_id' in columns:
            print("hospital_id column already exists in compare table")
            return
    
    # Add the column
    print("Adding hospital_id column to compare table...")
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE compare ADD COLUMN hospital_id VARCHAR(255)"))
    
    print("Migration complete: hospital_id column added to compare table")

if __name__ == "__main__":
    migrate_add_hospital_id()
