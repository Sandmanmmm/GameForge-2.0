#!/usr/bin/env python3
"""
Check existing enum types in PostgreSQL database
"""

import psycopg2
import os
from dotenv import load_dotenv

def check_enums():
    load_dotenv()
    
    conn = psycopg2.connect(
        host=os.getenv('DEV_DB_HOST'),
        port=os.getenv('DEV_DB_PORT'),
        database=os.getenv('DEV_DB_NAME'),
        user=os.getenv('DEV_DB_USER'),
        password=os.getenv('DEV_DB_PASSWORD')
    )
    
    cur = conn.cursor()
    
    # Check for existing enum types
    cur.execute("SELECT typname FROM pg_type WHERE typtype = 'e'")
    enums = cur.fetchall()
    
    print(f"Found {len(enums)} enum types:")
    for enum in enums:
        print(f"  - {enum[0]}")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    check_enums()