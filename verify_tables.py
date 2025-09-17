#!/usr/bin/env python3
"""
Simple script to verify database tables are created.
"""
import os
import sys
from sqlalchemy import create_engine, inspect

# Load environment variables
from dotenv import load_dotenv
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
        # Create engine and inspector
        engine = create_engine(database_url)
        inspector = inspect(engine)
        
        # Get all table names
        tables = inspector.get_table_names()
        
        print(f"✅ Successfully connected to database: {db_name}")
        print(f"📊 Total tables created: {len(tables)}")
        print("\n📋 Tables:")
        for table in sorted(tables):
            print(f"  - {table}")
            
        # Check for specific expected tables
        expected_tables = [
            'users', 'projects', 'assets', 'ai_requests', 'ml_models', 'datasets',
            'project_collaborations', 'project_invites', 'activity_logs', 'comments', 'notifications',
            'user_sessions', 'user_preferences', 'user_consents', 'user_permissions',
            'api_keys', 'audit_logs', 'storage_configs', 'system_config', 'game_templates'
        ]
        
        missing_tables = [table for table in expected_tables if table not in tables]
        
        if missing_tables:
            print(f"\n⚠️  Missing expected tables: {missing_tables}")
        else:
            print(f"\n✅ All expected tables are present!")
            
        # Show some table details
        print(f"\n🔍 Table details:")
        for table in ['users', 'projects', 'assets'][:3]:  # Show first 3 tables
            if table in tables:
                columns = inspector.get_columns(table)
                print(f"  {table}: {len(columns)} columns")
                
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())