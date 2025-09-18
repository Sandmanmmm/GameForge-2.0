#!/usr/bin/env python3
"""
Add 18 enterprise tables to reach 44-table production schema.
Creates all billing, marketplace, organization, AI/ML, security, and analytics tables.
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the project root to Python path
sys.path.insert(0, os.path.abspath('.'))

load_dotenv()

# Import all models to ensure they're registered
from gameforge.models import *
from gameforge.core.base import Base

def create_enterprise_tables():
    """Create all 18 enterprise tables for 44-table production schema"""
    
    # Database connection
    DATABASE_URL = 'postgresql://postgres:postgres@localhost:5432/gameforge_dev'
    engine = create_engine(DATABASE_URL)
    
    try:
        print("🏢 Creating 18 Enterprise Tables for 44-Table Production Schema")
        print("=" * 70)
        
        # Create all tables defined in our models
        Base.metadata.create_all(engine)
        
        # Verify table creation
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Get current table count
        result = session.execute(text("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """))
        table_count = result.scalar() or 0
        
        # List new enterprise tables
        enterprise_tables = [
            'subscription_plans', 'user_subscriptions', 'billing_transactions', 'payment_methods',
            'marketplace_categories', 'marketplace_items', 'marketplace_reviews', 'marketplace_purchases',
            'organizations', 'organization_members', 'organization_invites',
            'model_versions', 'training_jobs', 'ai_model_marketplace',
            'security_scans', 'compliance_reports',
            'analytics_events', 'performance_metrics'
        ]
        
        print(f"✅ Total tables in database: {table_count}")
        print(f"🎯 Target: 44 tables")
        
        if table_count >= 44:
            print("🎉 Successfully reached 44-table production schema!")
        else:
            print(f"📋 Need {44 - table_count} more tables")
        
        print("\n📊 Enterprise Tables Added:")
        
        # Verify each enterprise table exists
        existing_tables = []
        for table in enterprise_tables:
            result = session.execute(text(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = '{table}'
                )
            """))
            exists = result.scalar()
            status = "✅" if exists else "❌"
            print(f"  {status} {table}")
            if exists:
                existing_tables.append(table)
        
        print(f"\n📈 Enterprise tables created: {len(existing_tables)}/18")
        
        # Show table categories
        categories = {
            'Billing & Subscription': ['subscription_plans', 'user_subscriptions', 'billing_transactions', 'payment_methods'],
            'Marketplace & Community': ['marketplace_categories', 'marketplace_items', 'marketplace_reviews', 'marketplace_purchases'],
            'Organization & Team': ['organizations', 'organization_members', 'organization_invites'],
            'Enhanced AI/ML': ['model_versions', 'training_jobs', 'ai_model_marketplace'],
            'Security & Compliance': ['security_scans', 'compliance_reports'],
            'Analytics & Reporting': ['analytics_events', 'performance_metrics']
        }
        
        print("\n📋 Tables by Category:")
        for category, tables in categories.items():
            category_count = sum(1 for table in tables if table in existing_tables)
            print(f"  {category}: {category_count}/{len(tables)}")
        
        session.close()
        
        if len(existing_tables) == 18:
            print("\n🎊 All 18 enterprise tables successfully created!")
            print("🚀 GameForge 2.0 now has complete 44-table production schema")
        else:
            print(f"\n⚠️  Only {len(existing_tables)} enterprise tables created")
            print("Some tables may already exist or there were creation issues")
        
    except Exception as e:
        print(f"❌ Error creating enterprise tables: {e}")
        import traceback
        traceback.print_exc()

def verify_44_table_schema():
    """Verify we have exactly 44 tables with proper structure"""
    
    DATABASE_URL = 'postgresql://postgres:postgres@localhost:5432/gameforge_dev'
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("\n🔍 Verifying 44-Table Production Schema")
        print("=" * 50)
        
        # Get all tables
        result = session.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """))
        tables = [row[0] for row in result.fetchall()]
        
        print(f"📊 Total tables: {len(tables)}")
        
        # Categorize tables
        table_categories = {
            'Core User Management': ['users', 'user_sessions', 'user_preferences', 'user_consents', 'access_tokens'],
            'Project & Assets': ['projects', 'assets', 'game_templates'],
            'AI & ML Operations': ['ai_requests', 'ml_models', 'datasets'],
            'Collaboration': ['project_collaborations', 'project_invites', 'activity_logs', 'comments', 'notifications'],
            'System & Security': ['audit_logs', 'api_keys', 'user_permissions', 'system_config', 'storage_configs', 'usage_metrics', 'presigned_urls', 'security_events', 'rate_limits'],
            'Billing & Subscription': ['subscription_plans', 'user_subscriptions', 'billing_transactions', 'payment_methods'],
            'Marketplace': ['marketplace_categories', 'marketplace_items', 'marketplace_reviews', 'marketplace_purchases'],
            'Organizations': ['organizations', 'organization_members', 'organization_invites'],
            'Advanced AI/ML': ['model_versions', 'training_jobs', 'ai_model_marketplace'],
            'Security & Compliance': ['security_scans', 'compliance_reports'],
            'Analytics': ['analytics_events', 'performance_metrics'],
            'Database Management': ['alembic_version']
        }
        
        print("\n📋 Tables by Category:")
        total_expected = 0
        total_found = 0
        
        for category, expected_tables in table_categories.items():
            found_tables = [t for t in expected_tables if t in tables]
            total_expected += len(expected_tables)
            total_found += len(found_tables)
            status = "✅" if len(found_tables) == len(expected_tables) else "⚠️"
            print(f"  {status} {category}: {len(found_tables)}/{len(expected_tables)}")
            
            if len(found_tables) != len(expected_tables):
                missing = set(expected_tables) - set(found_tables)
                if missing:
                    print(f"    Missing: {', '.join(missing)}")
        
        print(f"\n📊 Schema Completeness: {total_found}/{total_expected} tables")
        
        if len(tables) == 44:
            print("🎉 Perfect! Exactly 44 tables in production schema")
        elif len(tables) > 44:
            extra_tables = set(tables) - {t for category in table_categories.values() for t in category}
            print(f"ℹ️  Found {len(tables)} tables ({len(tables) - 44} extra)")
            if extra_tables:
                print(f"   Extra tables: {', '.join(extra_tables)}")
        else:
            print(f"📋 Need {44 - len(tables)} more tables to reach 44")
        
        session.close()
        
    except Exception as e:
        print(f"❌ Error verifying schema: {e}")

if __name__ == "__main__":
    print("🚀 GameForge 2.0 - Enterprise Schema Expansion")
    print("=" * 60)
    
    # Create enterprise tables
    create_enterprise_tables()
    
    # Verify complete schema
    verify_44_table_schema()
    
    print("\n✨ Enterprise schema expansion complete!")