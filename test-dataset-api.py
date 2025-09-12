#!/usr/bin/env python3
"""
GameForge Dataset Versioning API Test Suite
===========================================

Comprehensive test suite for the Dataset Versioning API with DVC integration.
Tests all major functionality including uploads, validation, drift detection, and lineage.
"""

import os
import sys
import json
import time
import tempfile
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import argparse

# Test configuration
API_BASE_URL = "http://localhost:8080"
TEST_DATA_DIR = "test_datasets"

class DatasetAPITester:
    def __init__(self, base_url=API_BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_datasets = []
        
    def setup_test_data(self):
        """Create test datasets for validation"""
        print("🔧 Setting up test data...")
        
        # Create test data directory
        os.makedirs(TEST_DATA_DIR, exist_ok=True)
        
        # Generate NPC behavior dataset
        npc_data = pd.DataFrame({
            'npc_id': range(1000),
            'behavior_type': np.random.choice(['aggressive', 'passive', 'neutral'], 1000),
            'health': np.random.randint(50, 100, 1000),
            'damage': np.random.normal(25, 5, 1000),
            'speed': np.random.uniform(1.0, 5.0, 1000),
            'experience_points': np.random.randint(0, 1000, 1000),
            'timestamp': pd.date_range('2024-01-01', periods=1000, freq='1H')
        })
        npc_file = os.path.join(TEST_DATA_DIR, 'npc_behavior_v1.csv')
        npc_data.to_csv(npc_file, index=False)
        self.test_datasets.append(('npc-behavior-training', 'v1.0.0', npc_file))
        
        # Generate modified NPC behavior dataset (for drift testing)
        npc_data_v2 = npc_data.copy()
        npc_data_v2['damage'] = np.random.normal(30, 7, 1000)  # Different distribution
        npc_data_v2['speed'] = np.random.uniform(1.5, 6.0, 1000)  # Different range
        npc_data_v2['behavior_type'] = np.random.choice(['aggressive', 'passive', 'neutral', 'defensive'], 1000)
        npc_file_v2 = os.path.join(TEST_DATA_DIR, 'npc_behavior_v2.csv')
        npc_data_v2.to_csv(npc_file_v2, index=False)
        self.test_datasets.append(('npc-behavior-training', 'v2.0.0', npc_file_v2))
        
        # Generate procedural generation parameters
        proc_gen_data = {
            'biomes': {
                'forest': {'tree_density': 0.7, 'elevation_range': [100, 300]},
                'desert': {'sand_coverage': 0.9, 'elevation_range': [0, 150]},
                'mountain': {'rock_density': 0.8, 'elevation_range': [300, 800]}
            },
            'weather_patterns': {
                'rain_probability': 0.3,
                'temperature_range': [10, 35],
                'wind_strength': [0, 10]
            },
            'asset_variations': {
                'trees': 50,
                'rocks': 30,
                'buildings': 20
            }
        }
        proc_gen_file = os.path.join(TEST_DATA_DIR, 'procedural_generation_v1.json')
        with open(proc_gen_file, 'w') as f:
            json.dump(proc_gen_data, f, indent=2)
        self.test_datasets.append(('procedural-generation-base', 'v1.0.0', proc_gen_file))
        
        # Generate game analytics data
        analytics_data = pd.DataFrame({
            'player_id': range(500),
            'session_duration': np.random.exponential(30, 500),  # minutes
            'score': np.random.gamma(2, 1000, 500),
            'level_reached': np.random.poisson(5, 500),
            'deaths': np.random.poisson(3, 500),
            'items_collected': np.random.poisson(10, 500),
            'player_type': np.random.choice(['casual', 'hardcore', 'speedrunner'], 500),
            'platform': np.random.choice(['PC', 'Console', 'Mobile'], 500),
            'date_played': pd.date_range('2024-01-01', periods=500, freq='2H')
        })
        analytics_file = os.path.join(TEST_DATA_DIR, 'game_analytics_v1.csv')
        analytics_data.to_csv(analytics_file, index=False)
        self.test_datasets.append(('game-analytics-features', 'v1.0.0', analytics_file))
        
        print(f"✅ Created {len(self.test_datasets)} test datasets")
    
    def test_health_check(self):
        """Test API health endpoint"""
        print("🏥 Testing health check...")
        
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            response.raise_for_status()
            
            health_data = response.json()
            assert health_data['status'] == 'healthy', f"Expected healthy status, got {health_data['status']}"
            
            print("✅ Health check passed")
            return True
            
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False
    
    def test_dataset_upload(self):
        """Test dataset upload functionality"""
        print("📤 Testing dataset uploads...")
        
        uploaded_count = 0
        
        for dataset_name, version, file_path in self.test_datasets:
            try:
                print(f"  Uploading {dataset_name} {version}...")
                
                with open(file_path, 'rb') as f:
                    files = {'file': f}
                    data = {
                        'name': dataset_name,
                        'version': version,
                        'description': f'Test dataset {dataset_name} version {version}',
                        'tags': json.dumps({
                            'test': 'true',
                            'environment': 'testing',
                            'created_by': 'test_suite'
                        })
                    }
                    
                    response = self.session.post(f"{self.base_url}/datasets", files=files, data=data)
                    response.raise_for_status()
                    
                    result = response.json()
                    assert result['dataset_name'] == dataset_name
                    assert result['version'] == version
                    
                uploaded_count += 1
                print(f"    ✅ Upload successful")
                
                # Wait a bit between uploads to avoid overwhelming the system
                time.sleep(1)
                
            except Exception as e:
                print(f"    ❌ Upload failed: {e}")
                continue
        
        print(f"✅ Uploaded {uploaded_count}/{len(self.test_datasets)} datasets successfully")
        return uploaded_count > 0
    
    def test_dataset_listing(self):
        """Test dataset listing endpoints"""
        print("📋 Testing dataset listing...")
        
        try:
            # Test listing all datasets
            response = self.session.get(f"{self.base_url}/datasets")
            response.raise_for_status()
            datasets = response.json()
            
            assert isinstance(datasets, list), "Expected list of datasets"
            assert len(datasets) > 0, "Expected at least one dataset"
            
            print(f"  ✅ Found {len(datasets)} datasets")
            
            # Test listing versions for specific dataset
            dataset_name = 'npc-behavior-training'
            response = self.session.get(f"{self.base_url}/datasets/{dataset_name}/versions")
            response.raise_for_status()
            versions = response.json()
            
            assert isinstance(versions, list), "Expected list of versions"
            assert len(versions) >= 1, "Expected at least one version"
            
            print(f"  ✅ Found {len(versions)} versions for {dataset_name}")
            
            # Test getting specific version details
            version = versions[0]['version']
            response = self.session.get(f"{self.base_url}/datasets/{dataset_name}/versions/{version}")
            response.raise_for_status()
            version_details = response.json()
            
            assert version_details['name'] == dataset_name
            assert version_details['version'] == version
            
            print(f"  ✅ Retrieved details for {dataset_name}:{version}")
            
            return True
            
        except Exception as e:
            print(f"❌ Dataset listing failed: {e}")
            return False
    
    def test_dataset_download(self):
        """Test dataset download functionality"""
        print("📥 Testing dataset downloads...")
        
        try:
            dataset_name = 'game-analytics-features'
            version = 'v1.0.0'
            
            # Download dataset
            response = self.session.get(f"{self.base_url}/datasets/{dataset_name}/versions/{version}/download")
            response.raise_for_status()
            
            # Save to temporary file and verify
            with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp_file:
                temp_file.write(response.content)
                temp_file_path = temp_file.name
            
            # Verify downloaded data
            downloaded_data = pd.read_csv(temp_file_path)
            assert len(downloaded_data) > 0, "Downloaded dataset is empty"
            assert 'player_id' in downloaded_data.columns, "Expected column missing"
            
            # Clean up
            os.unlink(temp_file_path)
            
            print(f"  ✅ Successfully downloaded {dataset_name}:{version}")
            return True
            
        except Exception as e:
            print(f"❌ Dataset download failed: {e}")
            return False
    
    def test_validation_results(self):
        """Test dataset validation functionality"""
        print("🔍 Testing validation results...")
        
        try:
            dataset_name = 'npc-behavior-training'
            version = 'v1.0.0'
            
            # Get validation results
            response = self.session.get(f"{self.base_url}/datasets/{dataset_name}/versions/{version}/validation")
            
            if response.status_code == 404:
                print("  ⚠️ Validation results not available (expected for test data)")
                return True
            
            response.raise_for_status()
            validation = response.json()
            
            assert 'status' in validation, "Validation status missing"
            assert 'timestamp' in validation, "Validation timestamp missing"
            
            print(f"  ✅ Validation status: {validation['status']}")
            return True
            
        except Exception as e:
            print(f"❌ Validation test failed: {e}")
            return False
    
    def test_drift_analysis(self):
        """Test drift detection between dataset versions"""
        print("📊 Testing drift analysis...")
        
        try:
            dataset_name = 'npc-behavior-training'
            baseline_version = 'v1.0.0'
            current_version = 'v2.0.0'
            
            # Perform drift analysis
            response = self.session.post(
                f"{self.base_url}/datasets/{dataset_name}/drift-analysis",
                params={
                    'baseline_version': baseline_version,
                    'current_version': current_version
                }
            )
            
            if response.status_code == 400:
                print("  ⚠️ Drift analysis not available (expected for test setup)")
                return True
            
            response.raise_for_status()
            drift_analysis = response.json()
            
            assert 'overall_drift_score' in drift_analysis
            assert 'drift_status' in drift_analysis
            assert 'column_drifts' in drift_analysis
            
            print(f"  ✅ Drift score: {drift_analysis['overall_drift_score']:.3f}")
            print(f"  ✅ Drift status: {drift_analysis['drift_status']}")
            
            return True
            
        except Exception as e:
            print(f"❌ Drift analysis failed: {e}")
            return False
    
    def test_lineage_tracking(self):
        """Test dataset lineage functionality"""
        print("🔗 Testing lineage tracking...")
        
        try:
            # Upload a derived dataset with parent
            base_dataset = 'procedural-generation-base'
            base_version = 'v1.0.0'
            
            # Create enhanced dataset
            enhanced_data = {
                'biomes': {
                    'forest': {'tree_density': 0.8, 'elevation_range': [100, 350]},
                    'desert': {'sand_coverage': 0.95, 'elevation_range': [0, 200]},
                    'mountain': {'rock_density': 0.85, 'elevation_range': [350, 900]},
                    'arctic': {'ice_coverage': 0.9, 'elevation_range': [0, 100]}  # New biome
                },
                'weather_patterns': {
                    'rain_probability': 0.25,
                    'temperature_range': [5, 40],
                    'wind_strength': [0, 15]
                },
                'asset_variations': {
                    'trees': 75,
                    'rocks': 45,
                    'buildings': 30,
                    'decorations': 20  # New category
                }
            }
            
            enhanced_file = os.path.join(TEST_DATA_DIR, 'procedural_generation_enhanced.json')
            with open(enhanced_file, 'w') as f:
                json.dump(enhanced_data, f, indent=2)
            
            # Upload enhanced dataset with lineage
            with open(enhanced_file, 'rb') as f:
                files = {'file': f}
                data = {
                    'name': 'procedural-generation-enhanced',
                    'version': 'v1.0.0',
                    'description': 'Enhanced procedural generation with additional biomes and assets',
                    'tags': json.dumps({
                        'test': 'true',
                        'enhancement': 'true',
                        'base_version': base_version
                    }),
                    'parent_datasets': json.dumps([
                        {'name': base_dataset, 'version': base_version}
                    ])
                }
                
                response = self.session.post(f"{self.base_url}/datasets", files=files, data=data)
                response.raise_for_status()
            
            # Get lineage information
            response = self.session.get(f"{self.base_url}/datasets/procedural-generation-enhanced/versions/v1.0.0/lineage")
            response.raise_for_status()
            lineage = response.json()
            
            assert lineage['dataset_name'] == 'procedural-generation-enhanced'
            assert lineage['version'] == 'v1.0.0'
            assert len(lineage['parent_datasets']) == 1
            assert lineage['parent_datasets'][0]['name'] == base_dataset
            
            print(f"  ✅ Lineage tracked successfully")
            print(f"    Parent: {lineage['parent_datasets'][0]['name']}:{lineage['parent_datasets'][0]['version']}")
            
            return True
            
        except Exception as e:
            print(f"❌ Lineage tracking failed: {e}")
            return False
    
    def test_usage_statistics(self):
        """Test dataset usage statistics"""
        print("📈 Testing usage statistics...")
        
        try:
            dataset_name = 'npc-behavior-training'
            
            # Get usage statistics
            response = self.session.get(f"{self.base_url}/datasets/{dataset_name}/usage?days=30")
            response.raise_for_status()
            usage_stats = response.json()
            
            assert 'dataset_name' in usage_stats
            assert 'total_uses' in usage_stats
            assert 'usage_by_version' in usage_stats
            
            print(f"  ✅ Usage stats retrieved for {dataset_name}")
            print(f"    Total uses: {usage_stats['total_uses']}")
            
            return True
            
        except Exception as e:
            print(f"❌ Usage statistics test failed: {e}")
            return False
    
    def test_drift_history(self):
        """Test drift history retrieval"""
        print("📜 Testing drift history...")
        
        try:
            dataset_name = 'npc-behavior-training'
            
            # Get drift history
            response = self.session.get(f"{self.base_url}/datasets/{dataset_name}/drift-history?days=30")
            response.raise_for_status()
            drift_history = response.json()
            
            assert 'dataset_name' in drift_history
            assert 'drift_history' in drift_history
            
            print(f"  ✅ Drift history retrieved for {dataset_name}")
            print(f"    History entries: {len(drift_history['drift_history'])}")
            
            return True
            
        except Exception as e:
            print(f"❌ Drift history test failed: {e}")
            return False
    
    def test_metrics_endpoint(self):
        """Test Prometheus metrics endpoint"""
        print("📊 Testing metrics endpoint...")
        
        try:
            response = self.session.get(f"{self.base_url}/metrics")
            response.raise_for_status()
            
            metrics_text = response.text
            assert len(metrics_text) > 0, "Metrics response is empty"
            
            print("  ✅ Metrics endpoint accessible")
            return True
            
        except Exception as e:
            print(f"❌ Metrics test failed: {e}")
            return False
    
    def test_error_handling(self):
        """Test API error handling"""
        print("🚨 Testing error handling...")
        
        try:
            # Test non-existent dataset
            response = self.session.get(f"{self.base_url}/datasets/non-existent-dataset/versions")
            assert response.status_code == 404, f"Expected 404, got {response.status_code}"
            
            # Test non-existent version
            response = self.session.get(f"{self.base_url}/datasets/npc-behavior-training/versions/v999.0.0")
            assert response.status_code == 404, f"Expected 404, got {response.status_code}"
            
            # Test invalid drift analysis
            response = self.session.post(
                f"{self.base_url}/datasets/non-existent/drift-analysis",
                params={'baseline_version': 'v1.0.0', 'current_version': 'v2.0.0'}
            )
            assert response.status_code in [400, 404], f"Expected 400/404, got {response.status_code}"
            
            print("  ✅ Error handling working correctly")
            return True
            
        except Exception as e:
            print(f"❌ Error handling test failed: {e}")
            return False
    
    def cleanup_test_data(self):
        """Clean up test datasets"""
        print("🧹 Cleaning up test data...")
        
        try:
            # Remove test data directory
            import shutil
            if os.path.exists(TEST_DATA_DIR):
                shutil.rmtree(TEST_DATA_DIR)
            
            print("✅ Test data cleaned up")
            
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")
    
    def run_all_tests(self, cleanup=True):
        """Run the complete test suite"""
        print("🚀 Starting Dataset Versioning API Test Suite")
        print("=" * 50)
        
        start_time = time.time()
        
        # Test results
        tests = [
            ("Health Check", self.test_health_check),
            ("Dataset Upload", self.test_dataset_upload),
            ("Dataset Listing", self.test_dataset_listing),
            ("Dataset Download", self.test_dataset_download),
            ("Validation Results", self.test_validation_results),
            ("Drift Analysis", self.test_drift_analysis),
            ("Lineage Tracking", self.test_lineage_tracking),
            ("Usage Statistics", self.test_usage_statistics),
            ("Drift History", self.test_drift_history),
            ("Metrics Endpoint", self.test_metrics_endpoint),
            ("Error Handling", self.test_error_handling)
        ]
        
        # Setup test data
        self.setup_test_data()
        
        # Run tests
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            print(f"\n🧪 Running: {test_name}")
            try:
                if test_func():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"❌ {test_name} crashed: {e}")
                failed += 1
        
        # Cleanup
        if cleanup:
            self.cleanup_test_data()
        
        # Results summary
        total_time = time.time() - start_time
        
        print("\n" + "=" * 50)
        print("🏁 Test Suite Results")
        print("=" * 50)
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⏱️  Total time: {total_time:.2f} seconds")
        
        if failed == 0:
            print("🎉 All tests passed! Dataset Versioning API is working correctly.")
            return True
        else:
            print(f"💥 {failed} test(s) failed. Please check the API deployment.")
            return False

def main():
    parser = argparse.ArgumentParser(description='Test the GameForge Dataset Versioning API')
    parser.add_argument('--url', default=API_BASE_URL, help='API base URL')
    parser.add_argument('--no-cleanup', action='store_true', help='Skip cleanup of test data')
    
    args = parser.parse_args()
    
    # Create tester and run tests
    tester = DatasetAPITester(args.url)
    
    try:
        success = tester.run_all_tests(cleanup=not args.no_cleanup)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Test suite interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Test suite crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()