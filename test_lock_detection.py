#!/usr/bin/env python3
"""Test lock detection."""

import sys
sys.path.insert(0, 'custom_components/ezlopi')

# Import device_types module
exec(open('custom_components/ezlopi/device_types.py').read())

# Test cases for lock detection
test_cases = [
    {
        "name": "Doorlock - Direct Type",
        "input": {
            "name": "Front Door Lock",
            "deviceType": "doorlock",
            "valueType": "bool",
            "hasSetter": True,
            "value": True
        },
        "expected": {
            "platform": "lock",
            "device_class": "lock"
        }
    },
    {
        "name": "Lock - Name Pattern",
        "input": {
            "name": "main_lock",
            "valueType": "bool",
            "hasSetter": True,
            "value": False
        },
        "expected": {
            "platform": "lock",
            "device_class": "lock"
        }
    },
    {
        "name": "Deadbolt - Name Pattern",
        "input": {
            "name": "deadbolt_entry",
            "valueType": "bool",
            "hasSetter": True,
            "value": True
        },
        "expected": {
            "platform": "lock",
            "device_class": "lock"
        }
    },
    {
        "name": "Security Category with Door Lock",
        "input": {
            "name": "Back Door",
            "category": "security",
            "subcategory": "door_lock",
            "valueType": "bool",
            "hasSetter": True,
            "value": False
        },
        "expected": {
            "platform": "lock",
            "device_class": "lock"
        }
    },
    {
        "name": "Smart Lock with String Value",
        "input": {
            "name": "Smart Lock",
            "deviceType": "doorlock",
            "valueType": "string",
            "hasSetter": True,
            "value": "locked"
        },
        "expected": {
            "platform": "lock",
            "device_class": "lock"
        }
    },
    {
        "name": "Lock with User Codes Support",
        "input": {
            "name": "Keypad Lock",
            "deviceType": "doorlock",
            "valueType": "bool",
            "hasSetter": True,
            "supportsUserCodes": True,
            "value": True
        },
        "expected": {
            "platform": "lock",
            "device_class": "lock"
        }
    },
    {
        "name": "Lock with Battery Info",
        "input": {
            "name": "Battery Lock",
            "deviceType": "doorlock",
            "valueType": "bool",
            "hasSetter": True,
            "battery": 85,
            "value": False
        },
        "expected": {
            "platform": "lock",
            "device_class": "lock"
        }
    },
    {
        "name": "Regular Switch (not lock)",
        "input": {
            "name": "Light Switch",
            "valueType": "bool",
            "hasSetter": True,
            "value": True
        },
        "expected": {
            "platform": "switch",
            "device_class": "switch"
        }
    }
]

def run_tests():
    """Run all test cases and report results."""
    print("Testing Lock Detection")
    print("=" * 50)
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(test_cases, 1):
        result = detect_device_platform(test["input"])
        
        # Check if result matches expected
        platform_match = result.get("platform") == test["expected"]["platform"]
        class_match = result.get("device_class") == test["expected"]["device_class"]
        
        if platform_match and class_match:
            status = "✓ PASS"
            passed += 1
        else:
            status = "✗ FAIL"
            failed += 1
        
        print(f"\nTest {i}: {test['name']}")
        print(f"  Status: {status}")
        print(f"  Expected: platform={test['expected']['platform']}, class={test['expected']['device_class']}")
        print(f"  Got:      platform={result.get('platform')}, class={result.get('device_class')}")
        
        if not (platform_match and class_match):
            print(f"  ERROR: Mismatch detected!")
    
    print("\n" + "=" * 50)
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    
    if failed == 0:
        print("✓ All lock detection tests passed!")
    else:
        print(f"✗ {failed} test(s) failed")
    
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)