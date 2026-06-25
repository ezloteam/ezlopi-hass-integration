#!/usr/bin/env python3
"""Test script for device type detection improvements."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components'))

from ezlopi.device_types import detect_device_platform, DEVICE_TYPE_MAP

# Test cases based on different detection methods
test_cases = [
    # Test 1: Direct device type mapping
    {
        "name": "Motion Sensor - Direct Type",
        "input": {
            "name": "Living Room Motion",
            "deviceType": "sensor.motion",
            "valueType": "bool",
            "hasSetter": False
        },
        "expected": {
            "platform": "binary_sensor",
            "device_class": "motion"
        }
    },
    
    # Test 2: Door lock device
    {
        "name": "Smart Lock - Direct Type",
        "input": {
            "name": "Front Door Lock",
            "deviceType": "doorlock",
            "valueType": "token",
            "hasSetter": True
        },
        "expected": {
            "platform": "lock",
            "device_class": "lock"
        }
    },
    
    # Test 3: Dimmer outlet
    {
        "name": "Dimmer - Direct Type",
        "input": {
            "name": "Living Room Dimmer",
            "deviceType": "dimmer.outlet",
            "valueType": "int",
            "hasSetter": True,
            "value": 75
        },
        "expected": {
            "platform": "light",
            "device_class": "light"
        }
    },
    
    # Test 4: Category-based detection
    {
        "name": "Security Device - Category",
        "input": {
            "name": "Window Sensor",
            "category": "security",
            "subcategory": "window",
            "valueType": "bool",
            "hasSetter": False
        },
        "expected": {
            "platform": "binary_sensor",
            "device_class": "window"
        }
    },
    
    # Test 5: Name pattern detection
    {
        "name": "Motion - Name Pattern",
        "input": {
            "name": "motion_sensor_hallway",
            "valueType": "bool",
            "hasSetter": False
        },
        "expected": {
            "platform": "binary_sensor",
            "device_class": "motion"
        }
    },
    
    # Test 6: Temperature sensor
    {
        "name": "Temperature - Value Type",
        "input": {
            "name": "Room Temp",
            "valueType": "temperature",
            "scale": "celsius",
            "hasSetter": False
        },
        "expected": {
            "platform": "sensor",
            "device_class": "temperature"
        }
    },
    
    # Test 7: Regular switch
    {
        "name": "Switch - Bool with Setter",
        "input": {
            "name": "Power Switch",
            "valueType": "bool",
            "hasSetter": True
        },
        "expected": {
            "platform": "switch",
            "device_class": "switch"
        }
    },
    
    # Test 8: Battery sensor
    {
        "name": "Battery - Name Pattern",
        "input": {
            "name": "battery_level",
            "valueType": "int",
            "scale": "percent",
            "hasSetter": False,
            "value": 85
        },
        "expected": {
            "platform": "sensor",
            "device_class": "battery"
        }
    },
    
    # Test 9: Dimmer detection by value range
    {
        "name": "Dimmer - Value Range",
        "input": {
            "name": "brightness",
            "valueType": "int",
            "hasSetter": True,
            "scale": "percent",
            "value": 50
        },
        "expected": {
            "platform": "light",
            "device_class": "light"
        }
    },
    
    # Test 10: Generic sensor fallback
    {
        "name": "Generic Sensor - Fallback",
        "input": {
            "name": "custom_value",
            "valueType": "string",
            "hasSetter": False
        },
        "expected": {
            "platform": "sensor",
            "device_class": None
        }
    }
]

def run_tests():
    """Run all test cases and report results."""
    print("Testing Enhanced Device Type Detection")
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
        print(f"  Input: {test['input'].get('deviceType') or test['input'].get('name')}")
        print(f"  Expected: platform={test['expected']['platform']}, class={test['expected']['device_class']}")
        print(f"  Got:      platform={result.get('platform')}, class={result.get('device_class')}")
        
        if not (platform_match and class_match):
            print(f"  ERROR: Mismatch detected!")
    
    print("\n" + "=" * 50)
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    
    if failed == 0:
        print("✓ All tests passed!")
    else:
        print(f"✗ {failed} test(s) failed")
    
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)