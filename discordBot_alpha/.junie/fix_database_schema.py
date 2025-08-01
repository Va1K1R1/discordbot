import mysql.connector
import os
from dotenv import load_dotenv
import sys

# Load environment variables from .env file
load_dotenv()

def fix_database_schema():
    """Fix issues with the database schema."""
    print("Fixing database schema...")
    
    # Get database settings from environment variables
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = int(os.getenv('DB_PORT', 3306))
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    db_name = os.getenv('DB_NAME')
    
    try:
        # Connect to the database
        connection = mysql.connector.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            database=db_name
        )
        
        cursor = connection.cursor(dictionary=True)
        
        # 1. Fix message_type column in message_logs table
        print("\n1. Fixing message_type column in message_logs table...")
        
        # Check current column definition
        cursor.execute("DESCRIBE message_logs message_type")
        column_info = cursor.fetchone()
        print(f"Current message_type column: {column_info['Type']}")
        
        # Alter the column to include all required ENUM values
        alter_query = """
        ALTER TABLE message_logs 
        MODIFY COLUMN message_type ENUM('SEND', 'EDIT', 'DELETE', 'text', 'image', 'file', 'embed') NOT NULL
        """
        
        print(f"Executing: {alter_query}")
        cursor.execute(alter_query)
        connection.commit()
        
        # Verify the change
        cursor.execute("DESCRIBE message_logs message_type")
        column_info = cursor.fetchone()
        print(f"Updated message_type column: {column_info['Type']}")
        print("✅ message_type column fixed successfully!")
        
        # Close the connection
        cursor.close()
        connection.close()
        
        print("\nDatabase schema fixed successfully!")
        return True
        
    except mysql.connector.Error as err:
        print(f"❌ Error: {err}")
        return False

if __name__ == "__main__":
    success = fix_database_schema()
    sys.exit(0 if success else 1)