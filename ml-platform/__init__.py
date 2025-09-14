"""
ML Platform Package

This package provides comprehensive ML model management, monitoring, and deployment capabilities.
"""

__version__ = "1.0.0"

# Make key components available at package level
from .registry import ModelRegistry, ModelStage, Environment
from .monitoring import MLMonitor  
from .training import ExperimentTracker
from .archival import MLArchivalManager

__all__ = [
    "ModelRegistry",
    "ModelStage", 
    "Environment",
    "MLMonitor",
    "ExperimentTracker",
    "MLArchivalManager"
]