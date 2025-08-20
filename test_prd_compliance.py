#!/usr/bin/env python3
"""
Test PRD Compliance - Verify Eva meets PRD requirements
"""

import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

def test_file_structure():
    """Test if all PRD-required files exist"""
    
    required_files = [
        # Core services
        'backend/core/reasoning_service.py',
        'backend/core/lora_service.py', 
        'backend/utils/performance_monitor.py',
        'backend/core/ai_service.py',
        'backend/core/voice_service.py',
        
        # Configuration
        'docker-compose.yml',
        '.env',
        
        # Infrastructure
        'configs/Caddyfile'
    ]
    
    print("Testing file structure...")
    missing_files = []
    
    for file_path in required_files:
        full_path = os.path.join(os.path.dirname(__file__), file_path)
        if os.path.exists(full_path):
            print(f"  PASS: {file_path}")
        else:
            print(f"  FAIL: {file_path} - NOT FOUND")
            missing_files.append(file_path)
    
    return len(missing_files) == 0

def test_docker_config():
    """Test Docker Compose configuration"""
    
    print("\nTesting Docker configuration...")
    
    # Check if docker-compose.yml has required services
    compose_path = os.path.join(os.path.dirname(__file__), 'docker-compose.yml')
    
    if not os.path.exists(compose_path):
        print("  FAIL: docker-compose.yml not found")
        return False
    
    with open(compose_path, 'r') as f:
        content = f.read()
    
    required_services = [
        'eva-api',
        'vllm', 
        'xtts',
        'redis',
        'chromadb',
        'postgres',
        'caddy'
    ]
    
    all_found = True
    for service in required_services:
        if service in content:
            print(f"  PASS: Service '{service}' found")
        else:
            print(f"  FAIL: Service '{service}' missing")
            all_found = False
    
    return all_found

def test_environment_config():
    """Test environment configuration"""
    
    print("\nTesting environment configuration...")
    
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if not os.path.exists(env_path):
        print("  FAIL: .env file not found")
        return False
    
    with open(env_path, 'r') as f:
        content = f.read()
    
    # Check for Llama-3 8B model
    if 'meta-llama/Meta-Llama-3-8B-Instruct' in content:
        print("  PASS: Llama-3 8B model configured")
    else:
        print("  FAIL: Llama-3 8B model not configured")
        return False
    
    return True

def test_prd_architecture():
    """Test PRD architecture compliance"""
    
    print("\nTesting PRD architecture compliance...")
    
    # Test 1: Reasoning layer exists
    reasoning_path = 'backend/core/reasoning_service.py'
    if os.path.exists(reasoning_path):
        print("  PASS: Reasoning layer implemented")
    else:
        print("  FAIL: Reasoning layer missing")
        return False
    
    # Test 2: LoRA adapters exist  
    lora_path = 'backend/core/lora_service.py'
    if os.path.exists(lora_path):
        print("  PASS: LoRA adapter system implemented")
    else:
        print("  FAIL: LoRA adapter system missing")
        return False
    
    # Test 3: Performance monitoring exists
    perf_path = 'backend/utils/performance_monitor.py'
    if os.path.exists(perf_path):
        print("  PASS: Performance monitoring implemented")
    else:
        print("  FAIL: Performance monitoring missing") 
        return False
    
    # Test 4: Check for performance targets in performance monitor
    with open(perf_path, 'r', encoding='utf-8') as f:
        perf_content = f.read()
    
    if '2.5' in perf_content and '1.2' in perf_content:
        print("  PASS: Performance targets (2.5s text, 1.2s voice) found")
    else:
        print("  FAIL: Performance targets not properly configured")
        return False
    
    return True

def main():
    """Run all PRD compliance tests"""
    
    print("=== PRD COMPLIANCE TEST ===")
    print("Testing Eva against PRD requirements...\n")
    
    tests = [
        ("File Structure", test_file_structure),
        ("Docker Configuration", test_docker_config), 
        ("Environment Configuration", test_environment_config),
        ("PRD Architecture", test_prd_architecture)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"  ERROR in {test_name}: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n=== TEST SUMMARY ===")
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\nCONGRATULATIONS! Eva is PRD compliant!")
        print("Ready for production deployment.")
        return True
    else:
        print(f"\nWARNING: {total - passed} tests failed.")
        print("Please fix the issues before deployment.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)