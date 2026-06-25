#!/usr/bin/env python3
"""Test light/dimmer detection."""

import sys
sys.path.insert(0, 'custom_components/ezlopi')

# Import device_types module
exec(open('custom_components/ezlopi/device_types.py').read())

# Test cases for light detection
test_cases = [
    {
        "name": "Dimmer Outlet - Direct Type",
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
    {
        "name": "Dimmer In-wall - Direct Type",
        "input": {
            "name": "Bedroom Light",
            "deviceType": "dimmer.inwall",
            "valueType": "int",
            "hasSetter": True,
            "value": 50
        },
        "expected": {
            "platform": "light",
            "device_class": "light"
        }
    },
    {
        "name": "Dimmer - Name Pattern",
        "input": {
            "name": "kitchen_dimmer",
            "valueType": "int",
            "hasSetter": True,
            "scale": "percent",
            "value": 100
        },
        "expected": {
            "platform": "light",
            "device_class": "light"
        }
    },
    {
        "name": "Brightness Control - Name Pattern",
        "input": {
            "name": "brightness",
            "valueType": "int",
            "hasSetter": True,
            "value": 80
        },
        "expected": {
            "platform": "light",
            "device_class": "light"
        }
    },
    {
        "name": "Percent Scale Setter - Detection",
        "input": {
            "name": "light_control",
            "valueType": "int",
            "hasSetter": True,
            "scale": "percent",
            "value": 65
        },
        "expected": {
            "platform": "light",
            "device_class": "light"
        }
    },
    {
        "name": "Light Category with Dimmer",
        "input": {
            "name": "Main Light",
            "category": "light",
            "subcategory": "dimmer",
            "valueType": "int",
            "hasSetter": True,
            "value": 90
        },
        "expected": {
            "platform": "light",
            "device_class": "light"
        }
    },
    {
        "name": "Regular Switch (not dimmer)",
        "input": {
            "name": "Wall Switch",
            "valueType": "bool",
            "hasSetter": True,
            "value": True
        },
        "expected": {
            "platform": "switch",
            "device_class": "switch"
        }
    },
    {
        "name": "Sensor with Percent (not dimmer)",
        "input": {
            "name": "humidity",
            "valueType": "int",
            "hasSetter": False,
            "scale": "percent",
            "value": 45
        },
        "expected": {
            "platform": "sensor",
            "device_class": "humidity"
        }
    }
]

def run_tests():
    """Run all test cases and report results."""
    print("Testing Light/Dimmer Detection")
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
        print("✓ All light detection tests passed!")
    else:
        print(f"✗ {failed} test(s) failed")
    
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)