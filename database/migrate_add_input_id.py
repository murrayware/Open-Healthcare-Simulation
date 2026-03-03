# Migration: Add input_id column to outputs table
from database.users_table import engine
from sqlalchemy import text

def migrate():
    with engine.connect() as conn:
        try:
            # Add input_id column
            conn.execute(text('ALTER TABLE outputs ADD COLUMN input_id INTEGER'))
            conn.commit()
            print('✓ Added input_id column to outputs table')
        except Exception as e:
            if 'duplicate column name' in str(e).lower():
                print('✓ Column input_id already exists')
            else:
                print(f'✗ Error: {e}')
                raise

if __name__ == '__main__':
    migrate()
