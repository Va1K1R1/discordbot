import mysql.connector
import os
from dotenv import load_dotenv
import sys

# Load environment variables from .env file
load_dotenv()

def test_db_connection():
    """Test the database connection and verify tables."""
    print("Testing database connection...")
    
    # Get database settings from environment variables
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = int(os.getenv('DB_PORT', 3306))
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    db_name = os.getenv('DB_NAME')
    
    # Print connection settings (without password)
    print(f"Connection settings:")
    print(f"  Host: {db_host}")
    print(f"  Port: {db_port}")
    print(f"  User: {db_user}")
    print(f"  Database: {db_name}")
    
    try:
        # Try to connect to the database
        connection = mysql.connector.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            database=db_name
        )
        
        print("✅ Successfully connected to the database!")
        
        # Check if the required tables exist
        cursor = connection.cursor(dictionary=True)
        
        # Get list of tables
        cursor.execute("SHOW TABLES")
        tables = [table[f"Tables_in_{db_name}"] for table in cursor.fetchall()]
        
        print(f"\nFound {len(tables)} tables in the database:")
        for table in tables:
            print(f"  - {table}")
        
        # Check for specific tables mentioned in error logs
        required_tables = [
            "scheduled_deletions",
            "message_logs",
            "user_points",
            "point_transactions",
            "server_settings",
            "user_permissions"
        ]
        
        print("\nChecking for required tables:")
        for table in required_tables:
            if table in tables:
                print(f"  ✅ {table} - exists")
                
                # Check table structure for tables with issues in logs
                if table in ["scheduled_deletions", "message_logs"]:
                    cursor.execute(f"DESCRIBE {table}")
                    columns = cursor.fetchall()
                    print(f"    Columns in {table}:")
                    for column in columns:
                        print(f"      - {column['Field']} ({column['Type']})")
            else:
                print(f"  ❌ {table} - missing")
        
        # Close the connection
        cursor.close()
        connection.close()
        
    except mysql.connector.Error as err:
        print(f"❌ Error: {err}")
        return False
    
    return True

if __name__ == "__main__":
    success = test_db_connection()
    sys.exit(0 if success else 1)