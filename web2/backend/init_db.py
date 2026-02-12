import os
import mysql.connector

def apply_schema():
    # Read .env manually to avoid dependency issues if python-dotenv not installed
    db_config = {}
    try:
        with open('../../.env', 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, val = line.strip().split('=', 1)
                    if key in ('MYSQL_HOST', 'MYSQL_PORT', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_DATABASE'):
                        db_config[key] = val
    except FileNotFoundError:
        print("Error: .env file not found in parent directory")
        return

    config = {
        'host': db_config.get('MYSQL_HOST', '127.0.0.1'),
        'port': int(db_config.get('MYSQL_PORT', 3306)),
        'user': db_config.get('MYSQL_USER', 'root'),
        'password': db_config.get('MYSQL_PASSWORD', ''),
        'database': db_config.get('MYSQL_DATABASE', 'test'),
        'charset': 'utf8mb4',
    }
    
    print(f"Connecting to database: {config['host']}:{config['port']} / {config['database']}")

    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        
        with open('schema_v2.sql', 'r', encoding='utf-8') as f:
            sql_script = f.read()
            
        print("Executing schema_v2.sql...")
        for result in cursor.execute(sql_script, multi=True):
            if result.with_rows:
                result.fetchall()
        
        conn.commit()
        print("Schema applied successfully!")
        
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    apply_schema()
