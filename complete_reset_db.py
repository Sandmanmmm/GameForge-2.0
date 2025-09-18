#!/usr/bin/env python3
"""
Complete database reset including enums for fresh migration.
"""
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    # Create database URL from environment variables
    db_host = os.getenv('DEV_DB_HOST', 'localhost')
    db_port = os.getenv('DEV_DB_PORT', '5432')
    db_name = os.getenv('DEV_DB_NAME', 'gameforge_dev')
    db_user = os.getenv('DEV_DB_USER', 'postgres')
    db_password = os.getenv('DEV_DB_PASSWORD', 'postgres')
    
    database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    try:
        # Create engine
        engine = create_engine(database_url)
        
        print("🔥 Performing complete database reset...")
        
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                # Drop all tables first
                print("📋 Dropping all tables...")
                result = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'"))
                tables = [row[0] for row in result]
                
                for table in tables:
                    if table != 'alembic_version':  # Keep alembic version for now
                        print(f"  - Dropping table: {table}")
                        conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                
                # Drop all custom enum types
                print("🔤 Dropping all custom enum types...")
                result = conn.execute(text("""
                    SELECT t.typname 
                    FROM pg_type t 
                    JOIN pg_enum e ON t.oid = e.enumtypid 
                    GROUP BY t.typname
                """))
                enums = [row[0] for row in result]
                
                for enum_name in enums:
                    print(f"  - Dropping enum: {enum_name}")
                    conn.execute(text(f"DROP TYPE IF EXISTS {enum_name} CASCADE"))
                
                # Now drop alembic_version table to completely reset
                print("📦 Dropping alembic version table...")
                conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
                
                # Commit transaction
                trans.commit()
                print("✅ Complete database reset successful!")
                
            except Exception as e:
                trans.rollback()
                print(f"❌ Error during reset: {e}")
                return 1
                
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())