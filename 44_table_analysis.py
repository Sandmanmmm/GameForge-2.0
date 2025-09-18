#!/usr/bin/env python3
"""
Analysis of current 26 tables vs target 44 tables for GameForge 2.0 production schema.
Identifies the 18 additional tables needed for complete enterprise functionality.
"""

import psycopg2
from sqlalchemy import create_engine, inspect
import os
from dotenv import load_dotenv

load_dotenv()

# Current 26 tables
current_tables = [
    'access_tokens', 'activity_logs', 'ai_requests', 'alembic_version', 'api_keys',
    'assets', 'audit_logs', 'comments', 'datasets', 'game_templates', 'ml_models',
    'notifications', 'presigned_urls', 'project_collaborations', 'project_invites',
    'projects', 'rate_limits', 'security_events', 'storage_configs', 'system_config',
    'usage_metrics', 'user_consents', 'user_permissions', 'user_preferences',
    'user_sessions', 'users'
]

# Additional 18 tables needed for 44-table production schema
additional_tables_needed = {
    # Billing & Subscription (4 tables)
    'subscription_plans': 'Define available subscription tiers (free, pro, enterprise)',
    'user_subscriptions': 'Track user subscription status and billing cycles',
    'billing_transactions': 'Record payment transactions and invoices',
    'payment_methods': 'Store user payment method information',
    
    # Marketplace & Community (4 tables)
    'marketplace_items': 'Game assets, templates, and tools for sale/sharing',
    'marketplace_reviews': 'User reviews and ratings for marketplace items',
    'marketplace_categories': 'Organization categories for marketplace content',
    'marketplace_purchases': 'Track user purchases from marketplace',
    
    # Organization & Team Management (3 tables)
    'organizations': 'Company/team accounts with multiple users',
    'organization_members': 'User membership in organizations with roles',
    'organization_invites': 'Pending invitations to join organizations',
    
    # Enhanced AI/ML Features (3 tables)
    'model_versions': 'Track versions and deployments of ML models',
    'training_jobs': 'Background ML training job management',
    'ai_model_marketplace': 'Shared AI models and fine-tuned versions',
    
    # Advanced Security & Compliance (2 tables)
    'security_scans': 'Automated security vulnerability scans',
    'compliance_reports': 'GDPR, SOC2, and other compliance reporting',
    
    # Analytics & Reporting (2 tables)
    'analytics_events': 'Detailed user behavior and platform analytics',
    'performance_metrics': 'System performance and resource usage tracking'
}

def verify_current_tables():
    """Verify we have the expected 26 tables"""
    try:
        DATABASE_URL = 'postgresql://postgres:postgres@localhost:5432/gameforge_dev'
        engine = create_engine(DATABASE_URL)
        inspector = inspect(engine)
        
        actual_tables = sorted(inspector.get_table_names())
        expected_tables = sorted(current_tables)
        
        print("=== CURRENT TABLE VERIFICATION ===")
        print(f"Expected tables: {len(expected_tables)}")
        print(f"Actual tables: {len(actual_tables)}")
        
        if actual_tables == expected_tables:
            print("✅ All expected tables present")
        else:
            missing = set(expected_tables) - set(actual_tables)
            extra = set(actual_tables) - set(expected_tables)
            if missing:
                print(f"❌ Missing tables: {missing}")
            if extra:
                print(f"ℹ️  Extra tables: {extra}")
        
        return actual_tables
        
    except Exception as e:
        print(f"Database connection error: {e}")
        return []

def analyze_expansion_plan():
    """Analyze the 18 additional tables needed"""
    print("\n=== 44-TABLE EXPANSION ANALYSIS ===")
    print(f"Current tables: {len(current_tables)}")
    print(f"Target tables: 44")
    print(f"Additional needed: {len(additional_tables_needed)}")
    
    print("\n=== ADDITIONAL TABLES BY CATEGORY ===")
    
    categories = {
        'Billing & Subscription': ['subscription_plans', 'user_subscriptions', 'billing_transactions', 'payment_methods'],
        'Marketplace & Community': ['marketplace_items', 'marketplace_reviews', 'marketplace_categories', 'marketplace_purchases'],
        'Organization & Team Management': ['organizations', 'organization_members', 'organization_invites'],
        'Enhanced AI/ML Features': ['model_versions', 'training_jobs', 'ai_model_marketplace'],
        'Advanced Security & Compliance': ['security_scans', 'compliance_reports'],
        'Analytics & Reporting': ['analytics_events', 'performance_metrics']
    }
    
    for category, tables in categories.items():
        print(f"\n{category} ({len(tables)} tables):")
        for table in tables:
            print(f"  • {table}: {additional_tables_needed[table]}")
    
    return categories

def prioritize_implementation():
    """Prioritize which tables to implement first"""
    print("\n=== IMPLEMENTATION PRIORITY ===")
    
    priority_groups = {
        'Phase 1 - Core Business (6 tables)': [
            'subscription_plans', 'user_subscriptions', 'billing_transactions',
            'organizations', 'organization_members', 'analytics_events'
        ],
        'Phase 2 - Marketplace Foundation (5 tables)': [
            'marketplace_categories', 'marketplace_items', 'marketplace_reviews',
            'marketplace_purchases', 'payment_methods'
        ],
        'Phase 3 - Advanced Features (4 tables)': [
            'model_versions', 'training_jobs', 'organization_invites', 
            'performance_metrics'
        ],
        'Phase 4 - Enterprise & Compliance (3 tables)': [
            'ai_model_marketplace', 'security_scans', 'compliance_reports'
        ]
    }
    
    for phase, tables in priority_groups.items():
        print(f"\n{phase}:")
        for table in tables:
            print(f"  • {table}")
    
    return priority_groups

if __name__ == "__main__":
    print("🔍 GameForge 2.0 - 44 Table Production Schema Analysis")
    print("=" * 60)
    
    # Verify current state
    actual_tables = verify_current_tables()
    
    # Analyze expansion plan
    categories = analyze_expansion_plan()
    
    # Prioritize implementation
    priorities = prioritize_implementation()
    
    print(f"\n=== SUMMARY ===")
    print(f"✅ Current implementation: {len(current_tables)} tables")
    print(f"🎯 Target production schema: 44 tables")
    print(f"📋 Additional tables needed: {len(additional_tables_needed)} tables")
    print(f"🚀 Ready for phased implementation")
    
    if len(actual_tables) == 26:
        print("\n✅ Database is ready for 44-table expansion!")
    else:
        print(f"\n⚠️  Expected 26 tables, found {len(actual_tables)}. Review current schema first.")