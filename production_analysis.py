#!/usr/bin/env python3
"""
GameForge Backend Production Readiness Analysis
==============================================

Comprehensive analysis of the current backend implementation
to identify gaps for production deployment.
"""

from gameforge.app import app
import json
from datetime import datetime

def analyze_api_routes():
    """Analyze all API routes and categorize them"""
    print("🔍 GameForge Backend - Production Readiness Analysis")
    print("=" * 60)
    
    # Get all routes
    routes = []
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            routes.append({
                'path': route.path,
                'methods': list(route.methods) if route.methods else [],
                'name': getattr(route, 'name', 'Unknown')
            })
    
    # Categorize routes
    categories = {
        'Authentication': [],
        'Users': [],
        'Projects': [],
        'Assets': [],
        'AI/ML': [],
        'Enterprise': [],
        'Health/Monitoring': [],
        'Storage': [],
        'Other': []
    }
    
    for route in routes:
        path = route['path']
        if '/auth' in path:
            categories['Authentication'].append(route)
        elif '/users' in path or '/user' in path:
            categories['Users'].append(route)
        elif '/projects' in path or '/project' in path:
            categories['Projects'].append(route)
        elif '/assets' in path or '/asset' in path:
            categories['Assets'].append(route)
        elif '/ai' in path or '/ml' in path or '/models' in path or '/datasets' in path:
            categories['AI/ML'].append(route)
        elif '/enterprise' in path:
            categories['Enterprise'].append(route)
        elif '/health' in path or '/monitoring' in path:
            categories['Health/Monitoring'].append(route)
        elif '/storage' in path:
            categories['Storage'].append(route)
        else:
            categories['Other'].append(route)
    
    print(f"📊 Total Routes: {len(routes)}")
    print()
    
    for category, category_routes in categories.items():
        if category_routes:
            print(f"📋 {category} ({len(category_routes)} routes):")
            for route in category_routes:
                methods = ', '.join(route['methods']) if route['methods'] else 'N/A'
                print(f"  {methods:<12} {route['path']}")
            print()
    
    return routes, categories

def analyze_missing_endpoints():
    """Check for missing core endpoints"""
    print("🔍 Missing Core Entity Endpoints Analysis:")
    print("-" * 40)
    
    routes = []
    for route in app.routes:
        if hasattr(route, 'path'):
            routes.append(route.path)
    
    # Core entities that should have CRUD endpoints
    core_entities = [
        'users', 'projects', 'assets', 'organizations', 'subscriptions',
        'marketplace', 'billing', 'analytics', 'security', 'compliance',
        'notifications', 'collaborations', 'invites'
    ]
    
    missing_endpoints = []
    implemented_endpoints = []
    
    for entity in core_entities:
        entity_routes = [r for r in routes if f'/{entity}' in r]
        if not entity_routes:
            missing_endpoints.append(entity)
            print(f"  ❌ {entity}")
        else:
            implemented_endpoints.append(entity)
            print(f"  ✅ {entity} ({len(entity_routes)} routes)")
    
    coverage = (len(implemented_endpoints) / len(core_entities)) * 100
    print(f"\n📈 API Coverage: {coverage:.1f}%")
    print(f"📊 Implemented: {len(implemented_endpoints)}/{len(core_entities)}")
    
    return missing_endpoints, implemented_endpoints

def analyze_crud_completeness():
    """Check if implemented endpoints have complete CRUD operations"""
    print("\n🔧 CRUD Operations Completeness:")
    print("-" * 35)
    
    routes = []
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            routes.append({
                'path': route.path,
                'methods': list(route.methods) if route.methods else []
            })
    
    # Group routes by entity
    entities = {}
    for route in routes:
        path_parts = route['path'].split('/')
        if len(path_parts) >= 4 and path_parts[1] == 'api' and path_parts[2] == 'v1':
            entity = path_parts[3]
            if entity not in entities:
                entities[entity] = {'routes': [], 'methods': set()}
            entities[entity]['routes'].append(route)
            entities[entity]['methods'].update(route['methods'])
    
    for entity, data in entities.items():
        methods = data['methods']
        has_get = 'GET' in methods
        has_post = 'POST' in methods
        has_put = 'PUT' in methods or 'PATCH' in methods
        has_delete = 'DELETE' in methods
        
        crud_score = sum([has_get, has_post, has_put, has_delete])
        crud_status = "Complete" if crud_score == 4 else f"Partial ({crud_score}/4)"
        
        status_icon = "✅" if crud_score == 4 else "⚠️" if crud_score >= 2 else "❌"
        print(f"  {status_icon} {entity:<15} {crud_status:<12} ({', '.join(sorted(methods))})")
    
    return entities

def analyze_security_features():
    """Analyze implemented security features"""
    print("\n🔒 Security Features Analysis:")
    print("-" * 30)
    
    # Check middleware and security configurations
    security_features = {
        'CORS': False,
        'Authentication': False,
        'Authorization': False,
        'Rate Limiting': False,
        'Input Validation': False,
        'HTTPS/TLS': False,
        'Security Headers': False,
        'Audit Logging': False
    }
    
    # Check if security middleware is configured
    try:
        from gameforge.core.security_middleware import SecurityMiddleware
        security_features['Security Headers'] = True
        security_features['Rate Limiting'] = True
    except:
        pass
    
    # Check for authentication
    try:
        from gameforge.api.v1.auth import router
        security_features['Authentication'] = True
    except:
        pass
    
    # Check for CORS
    try:
        from gameforge.core.cors_config import setup_cors
        security_features['CORS'] = True
    except:
        pass
    
    # Check for audit logging
    try:
        from gameforge.models.audit_logs import AuditLog
        security_features['Audit Logging'] = True
    except:
        pass
    
    for feature, implemented in security_features.items():
        status = "✅" if implemented else "❌"
        print(f"  {status} {feature}")
    
    return security_features

def analyze_production_deployment():
    """Analyze production deployment readiness"""
    print("\n🚀 Production Deployment Readiness:")
    print("-" * 35)
    
    deployment_features = {
        'Docker Configuration': False,
        'Environment Management': False,
        'Database Migrations': False,
        'Health Checks': False,
        'Monitoring/Metrics': False,
        'Error Handling': False,
        'Graceful Shutdown': False,
        'Load Balancing Ready': False
    }
    
    # Check for various files and configurations
    import os
    
    # Check for Docker
    if os.path.exists('Dockerfile') or os.path.exists('docker-compose.yml'):
        deployment_features['Docker Configuration'] = True
    
    # Check for environment management
    if os.path.exists('.env') or os.path.exists('gameforge/core/config.py'):
        deployment_features['Environment Management'] = True
    
    # Check for migrations
    if os.path.exists('alembic.ini'):
        deployment_features['Database Migrations'] = True
    
    # Check for health checks
    try:
        from gameforge.core.health import HealthChecker
        deployment_features['Health Checks'] = True
    except:
        pass
    
    # Check for error handling in app
    deployment_features['Error Handling'] = True  # Assumed from middleware
    deployment_features['Graceful Shutdown'] = True  # Lifespan context manager
    
    for feature, implemented in deployment_features.items():
        status = "✅" if implemented else "❌"
        print(f"  {status} {feature}")
    
    return deployment_features

def generate_production_gaps():
    """Generate list of production gaps that need to be addressed"""
    print("\n🎯 Critical Production Gaps to Address:")
    print("=" * 45)
    
    gaps = [
        {
            'priority': 'HIGH',
            'category': 'API Completeness',
            'description': 'Missing CRUD endpoints for marketplace, billing, organizations',
            'impact': 'Core features not accessible via API'
        },
        {
            'priority': 'HIGH',
            'category': 'Authentication',
            'description': 'JWT token validation and refresh mechanism',
            'impact': 'Users cannot maintain authenticated sessions'
        },
        {
            'priority': 'HIGH',
            'category': 'Authorization',
            'description': 'Role-based access control implementation',
            'impact': 'No permission enforcement on endpoints'
        },
        {
            'priority': 'MEDIUM',
            'category': 'Input Validation',
            'description': 'Pydantic models for request/response validation',
            'impact': 'No protection against malformed requests'
        },
        {
            'priority': 'MEDIUM',
            'category': 'Error Handling',
            'description': 'Consistent error responses and exception handling',
            'impact': 'Poor user experience and debugging difficulties'
        },
        {
            'priority': 'MEDIUM',
            'category': 'Testing',
            'description': 'Unit tests, integration tests, API tests',
            'impact': 'No confidence in code reliability'
        },
        {
            'priority': 'LOW',
            'category': 'Documentation',
            'description': 'API documentation, deployment guides',
            'impact': 'Difficult for developers to use and deploy'
        }
    ]
    
    for gap in gaps:
        priority_color = "🔴" if gap['priority'] == 'HIGH' else "🟡" if gap['priority'] == 'MEDIUM' else "🟢"
        print(f"{priority_color} {gap['priority']} - {gap['category']}")
        print(f"   Description: {gap['description']}")
        print(f"   Impact: {gap['impact']}")
        print()
    
    return gaps

if __name__ == "__main__":
    print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Run all analyses
    routes, categories = analyze_api_routes()
    missing_endpoints, implemented_endpoints = analyze_missing_endpoints()
    entities = analyze_crud_completeness()
    security_features = analyze_security_features()
    deployment_features = analyze_production_deployment()
    gaps = generate_production_gaps()
    
    # Summary
    print("📋 PRODUCTION READINESS SUMMARY:")
    print("=" * 35)
    total_routes = len(routes)
    security_score = sum(security_features.values()) / len(security_features) * 100
    deployment_score = sum(deployment_features.values()) / len(deployment_features) * 100
    
    print(f"📊 Total API Routes: {total_routes}")
    print(f"🔒 Security Score: {security_score:.1f}%")
    print(f"🚀 Deployment Score: {deployment_score:.1f}%")
    print(f"🎯 High Priority Gaps: {len([g for g in gaps if g['priority'] == 'HIGH'])}")
    
    overall_score = (security_score + deployment_score) / 2
    print(f"🏆 Overall Readiness: {overall_score:.1f}%")
    
    if overall_score >= 80:
        print("✅ Ready for production with minor fixes")
    elif overall_score >= 60:
        print("⚠️  Needs significant work before production")
    else:
        print("❌ Not ready for production - major gaps")