#!/usr/bin/env python3
"""Test binary sensor detection and implementation."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components'))

from ezlopi.device_types import detect_device_platform

# Test cases for binary sensor detection
test_cases = [
    {
        "name": "Motion Sensor - Direct Type",
        "input": {
            "name": "Living Room Motion",
            "deviceType": "sensor.motion",
            "valueType": "bool",
            "hasSetter": False,
            "value": False
        },
        "expected": {
            "platform": "binary_sensor",
            "device_class": "motion"
        }
    },
    {
        "name": "Door Sensor - Direct Type",
        "input": {
            "name": "Front Door",
            "deviceType": "sensor.door",
            "valueType": "bool",
            "hasSetter": False,
            "value": True
        },
        "expected": {
            "platform": "binary_sensor",
            "device_class": "door"
        }
    },
    {
        "name": "Window Sensor - Direct Type",
        "input": {
            "name": "Bedroom Window",
            "deviceType": "sensor.window",
            "valueType": "bool",
            "hasSetter": False,
            "value": False
        },
        "expected": {
            "platform": "binary_sensor",
            "device_class": "window"
        }
    },
    {
        "name": "Motion - Name Pattern",
        "input": {
            "name": "hallway_motion_sensor",
            "valueType": "bool",
            "hasSetter": False,
            "value": True
        },
        "expected": {
            "platform": "binary_sensor",
            "device_class": "motion"
        }
    },
    {
        "name": "Door - Name Pattern",
        "input": {
            "name": "garage_door",
            "valueType": "bool",
            "hasSetter": False,
            "value": False
        },
        "expected": {
            "platform": "binary_sensor",
            "device_class": "door"
        }
    },
    {
        "name": "Tamper Sensor - Name Pattern",
        "input": {
            "name": "lock_tamper",
            "valueType": "bool",
            "hasSetter": False,
            "value": False
        },
        "expected": {
            "platform": "binary_sensor",
            "device_class": "tamper"
        }
    },
    {
        "name": "Smoke Detector - Name Pattern",
        "input": {
            "name": "smoke_alarm",
            "valueType": "bool",
            "hasSetter": False,
            "value": False
        },
        "expected": {
            "platform": "binary_sensor",
            "device_class": "smoke"
        }
    },
    {
        "name": "Water Leak - Name Pattern",
        "input": {
            "name": "basement_water_sensor",
            "valueType": "bool",
            "hasSetter": False,
            "value": False
        },
        "expected": {
            "platform": "binary_sensor",
            "device_class": "moisture"
        }
    },
    {
        "name": "Security Category - Door",
        "input": {
            "name": "Security Sensor",
            "category": "security",
            "subcategory": "door",
            "valueType": "bool",
            "hasSetter": False,
            "value": True
        },
        "expected": {
            "platform": "binary_sensor",
            "device_class": "door"
        }
    },
    {
        "name": "Generic Bool without Setter",
        "input": {
            "name": "some_sensor",
            "valueType": "bool",
            "hasSetter": False,
            "value": False
        },
        "expected": {
            "platform": "binary_sensor",
            "device_class": None
        }
    }
]

def run_tests():
    """Run all test cases and report results."""
    print("Testing Binary Sensor Detection")
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
        print("✓ All binary sensor tests passed!")
    else:
        print(f"✗ {failed} test(s) failed")
    
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)