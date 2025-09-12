#!/usr/bin/env python3
"""
========================================================================
GameForge AI - File Audit & Classification Report
Comprehensive analysis of file bulk, usage patterns, and cleanup recommendations
========================================================================
"""

import os
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def analyze_repository():
    """Comprehensive repository file analysis"""
    
    print("🔍 GAMEFORGE AI REPOSITORY AUDIT")
    print("=" * 80)
    
    # Size breakdown from the audit
    size_analysis = {
        "MASSIVE (Multi-GB)": {
            "services": "71.63 GB",
            "backup_local_changes": "13.60 GB", 
            ".venv": "2.09 GB",
            ".git": "970.59 MB"
        },
        "LARGE (100MB+)": {
            "node_modules": "370.53 MB",
            "backups": "25.60 MB"
        },
        "MEDIUM (1-10MB)": {
            "sbom": "5.86 MB",
            "kind.exe": "6.26 MB",
            "src": "1.38 MB",
            "dist": "1.36 MB",
            "backend": "1.30 MB",
            "GameForge_VSCode_Jupyter_Integration.ipynb": "1.32 MB"
        },
        "SMALL (Under 1MB)": {
            "scripts": "774.43 KB",
            "security-scans": "275.55 KB",
            "monitoring": "163.93 KB",
            "k8s": "138.51 KB",
            "secrets": "137.29 KB"
        }
    }
    
    # File count analysis - Total: 105,084 files
    file_count_analysis = {
        "MASSIVE": {
            ".venv": "46,938 files (44.6%)",
            "node_modules": "48,083 files (45.7%)",
            "services": "228 files",
            "backup_local_changes": "8,842 files (8.4%)"
        },
        "ACTIVE": {
            "src": "123 files",
            "backend": "80 files", 
            "scripts": "61 files",
            "k8s": "55 files",
            "monitoring": "42 files"
        }
    }
    
    print("\n📊 SIZE DISTRIBUTION ANALYSIS")
    print("-" * 50)
    total_size_gb = 89.7  # Approximate total
    
    for category, items in size_analysis.items():
        print(f"\n{category}:")
        for name, size in items.items():
            print(f"  📁 {name}: {size}")
    
    print(f"\n🎯 TOTAL REPOSITORY SIZE: ~{total_size_gb:.1f} GB")
    print(f"🗂️  TOTAL FILE COUNT: 105,084 files")
    
    # File classification
    classification = {
        "🟢 ACTIVE (Production Critical)": [
            "Dockerfiles (production, gpu-workload, vastai-gpu, k8s)",
            "docker-compose.production*.yml files",
            "k8s/manifests/* (8 production K8s files)",
            "helm/gameforge/* (Helm chart)",
            "scripts/*.py (61 Python automation scripts)",
            "src/* (123 source code files)", 
            "backend/* (80 backend files)",
            "CI/CD workflows (.github/workflows/)",
            "nginx-hardened.conf, nginx-json-logging.conf",
            "scaling-configs/* (18 K8s scaling files)",
            "migration/* (production migration scripts)",
            "ops/* (11 operations automation files)"
        ],
        
        "🟡 LEGACY (Older Versions)": [
            "docker-compose.phase*.yml (phase2, phase4, phase5)",
            "Dockerfile.minimal, Dockerfile.optimized", 
            "phase1-*.ps1, phase3-*.ps1, phase5-*.ps1 scripts",
            "build-phase*.ps1 (older build scripts)",
            "deploy-phase*.ps1 (older deployment scripts)",
            "validate-phase*.ps1 (older validation scripts)", 
            ".env.phase* (phase-specific environments)",
            "PHASE_*_IMPLEMENTATION.md documentation",
            "backup/* directory (4 files, 19.72 KB)",
            "phase5-test-reports/* (older test results)"
        ],
        
        "🔴 GENERATED (Build Outputs)": [
            "node_modules/* (48,083 files, 370.53 MB)",
            ".venv/* (46,938 files, 2.09 GB)", 
            "package-lock.json (342.53 KB)",
            "dist/* (build outputs, 1.36 MB)",
            "sbom/* (SBOM files, 5.86 MB)",
            "kind.exe (downloaded binary, 6.26 MB)",
            "backups/* (backup files, 25.60 MB)",
            "security-scans/* (scan results, 275.55 KB)",
            "logs/* (runtime logs, 46.82 KB)",
            "certs/* (generated certificates)"
        ],
        
        "⚫ AMBIGUOUS (Unclear Status)": [
            "services/* (71.63 GB - MASSIVE, unclear if active)",
            "backup_local_changes/* (13.60 GB backup)",
            "vast_deployment_notebook.ipynb (43.41 KB)",
            "GameForge_VSCode_Jupyter_Integration.ipynb (1.32 MB)",
            "docker-compose.vastai*.yml (VastAI deployment configs)",
            "gameforge-ai-rtx4090.Dockerfile vs gameforge-ai.Dockerfile",
            "Multiple .env files (.env, .env.production, .env.security, etc.)",
            "Multiple requirements*.txt files (minimal, production, gpu, etc.)",
            "SSL certificates and vault secrets (production vs development)"
        ]
    }
    
    print("\n🏷️  FILE CLASSIFICATION")
    print("=" * 60)
    
    for category, files in classification.items():
        print(f"\n{category}")
        print("-" * (len(category) - 4))
        for file in files:
            print(f"  • {file}")
    
    # Critical findings
    print("\n🚨 CRITICAL FINDINGS")
    print("=" * 40)
    
    critical_issues = [
        "📦 DEPENDENCY BLOAT: node_modules (370MB) + .venv (2GB) = 45.7% of total files",
        "🗃️  SERVICES MYSTERY: 71.63 GB in services/ directory needs investigation", 
        "💾 BACKUP REDUNDANCY: 13.60 GB in backup_local_changes + 25.60 MB in backups/",
        "📋 PHASE LEGACY: Multiple phase* files suggest incremental development artifacts",
        "🔧 ENVIRONMENT PROLIFERATION: 15+ .env files with unclear relationships",
        "🐳 DOCKERFILE VARIANTS: 15+ Dockerfiles with overlapping purposes"
    ]
    
    for issue in critical_issues:
        print(f"  {issue}")
    
    # Cleanup recommendations
    print("\n🧹 CLEANUP RECOMMENDATIONS")
    print("=" * 45)
    
    cleanup_actions = {
        "🔥 IMMEDIATE (High Impact)": [
            "Investigate services/ directory (71.63 GB) - largest space consumer",
            "Remove .venv if reproducible (2.09 GB, 46K files)",
            "Remove node_modules if package.json exists (370MB, 48K files)",
            "Archive backup_local_changes to external storage (13.60 GB)"
        ],
        
        "📦 MEDIUM PRIORITY": [
            "Consolidate legacy phase* files into archive/legacy/",
            "Remove duplicate Dockerfiles (keep production variants)",
            "Clean up old .env.phase* files",
            "Archive phase*-reports/ directories",
            "Remove generated SBOM files if reproducible (5.86 MB)"
        ],
        
        "🔧 LOW PRIORITY": [
            "Standardize requirements.txt files (keep minimal set)",
            "Consolidate security scan results",
            "Clean up duplicate backup files",
            "Archive old logs and temporary certificates"
        ]
    }
    
    for priority, actions in cleanup_actions.items():
        print(f"\n{priority}")
        print("-" * (len(priority) - 4))
        for action in actions:
            print(f"  • {action}")
    
    # Space savings potential
    print("\n💰 POTENTIAL SPACE SAVINGS")
    print("=" * 35)
    
    savings = [
        "🎯 AGGRESSIVE CLEANUP: ~87 GB (97% reduction)",
        "   • services/ investigation: ~71.63 GB",
        "   • backup_local_changes removal: ~13.60 GB", 
        "   • .venv removal: ~2.09 GB",
        "",
        "⚡ MODERATE CLEANUP: ~400 MB (node_modules + sbom + backups)",
        "",
        "🧹 CONSERVATIVE CLEANUP: ~50 MB (logs + temp files + duplicates)"
    ]
    
    for saving in savings:
        print(f"  {saving}")
    
    print("\n" + "=" * 80)
    print("🎉 AUDIT COMPLETE - Repository analysis finished")
    print(f"📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    analyze_repository()