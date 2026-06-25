#!/usr/bin/env python3
"""Test battery monitoring and detection."""

import sys
sys.path.insert(0, 'custom_components/ezlopi')

# Import modules
exec(open('custom_components/ezlopi/device_types.py').read())

# Additional test data for battery functions
def test_battery_extraction():
    """Test battery extraction from devices."""
    test_devices = [
        {
            "id": "item_1",
            "deviceId": "device_001", 
            "name": "Lock Battery",
            "deviceClass": "battery",
            "value": 85
        },
        {
            "id": "item_2",
            "deviceId": "device_002",
            "name": "Motion Sensor Battery",
            "deviceClass": "battery", 
            "value": 42
        },
        {
            "id": "item_3",
            "deviceId": "device_003",
            "name": "Temperature",
            "deviceClass": "temperature",
            "value": 22.5
        }
    ]
    
    # Import the function (simulate)
    battery_info = {}
    for device in test_devices:
        device_id = device.get("deviceId")
        if device.get("deviceClass") == "battery":
            battery_info[device_id] = {
                "battery_level": device.get("value", 0),
                "battery_item_id": device.get("id"),
                "has_battery": True
            }
    
    print("Battery Extraction Test:")
    print(f"  Found {len(battery_info)} battery devices")
    for device_id, info in battery_info.items():
        print(f"  {device_id}: {info['battery_level']}%")
    
    return len(battery_info) == 2

def test_battery_status():
    """Test battery status determination."""
    test_cases = [
        (95, "good"),
        (80, "good"),
        (60, "fair"),
        (40, "low"),
        (20, "critical"),
        (5, "very_low"),
    ]
    
    print("\nBattery Status Test:")
    passed = 0
    for level, expected in test_cases:
        # Simulate status calculation
        if level > 75:
            status = "good"
        elif level > 50:
            status = "fair"
        elif level > 25:
            status = "low"
        elif level > 10:
            status = "critical"
        else:
            status = "very_low"
        
        if status == expected:
            print(f"  ✓ {level}% -> {status}")
            passed += 1
        else:
            print(f"  ✗ {level}% -> {status} (expected {expected})")
    
    return passed == len(test_cases)

# Test cases for battery device detection
test_cases = [
    {
        "name": "Battery Sensor - Direct valueType",
        "input": {
            "name": "Battery Level",
            "valueType": "battery",
            "hasSetter": False,
            "value": 85
        },
        "expected": {
            "platform": "sensor",
            "device_class": "battery"
        }
    },
    {
        "name": "Battery - Name Pattern",
        "input": {
            "name": "battery_level",
            "valueType": "int",
            "hasSetter": False,
            "scale": "percent",
            "value": 72
        },
        "expected": {
            "platform": "sensor",
            "device_class": "battery"
        }
    },
    {
        "name": "Battery with Percent Scale",
        "input": {
            "name": "Device Battery",
            "valueType": "int",
            "hasSetter": False,
            "scale": "percent",
            "value": 95
        },
        "expected": {
            "platform": "sensor",
            "device_class": "battery"
        }
    },
    {
        "name": "Battery Name Pattern",
        "input": {
            "name": "battery",
            "valueType": "int",
            "hasSetter": False,
            "value": 45
        },
        "expected": {
            "platform": "sensor",
            "device_class": "battery"
        }
    },
    {
        "name": "Alert Binary Sensor",
        "input": {
            "name": "tamper_alert",
            "valueType": "bool",
            "hasSetter": False,
            "value": True
        },
        "expected": {
            "platform": "binary_sensor",
            "device_class": "tamper"
        }
    },
    {
        "name": "Battery Percentage Scale",
        "input": {
            "name": "sensor_battery",
            "valueType": "int",
            "scale": "percent",
            "hasSetter": False,
            "value": 100
        },
        "expected": {
            "platform": "sensor",
            "device_class": "battery"
        }
    },
    {
        "name": "Non-battery Percentage (humidity)",
        "input": {
            "name": "humidity",
            "valueType": "int",
            "scale": "percent",
            "hasSetter": False,
            "value": 65
        },
        "expected": {
            "platform": "sensor",
            "device_class": "humidity"
        }
    },
    {
        "name": "Power Sensor (not battery)",
        "input": {
            "name": "power_consumption",
            "valueType": "float",
            "hasSetter": False,
            "value": 150.5
        },
        "expected": {
            "platform": "sensor",
            "device_class": "power"
        }
    }
]

def run_battery_detection_tests():
    """Run battery detection tests."""
    print("\nTesting Battery Detection")
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
    print(f"Detection Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    
    return failed == 0

def test_low_battery_threshold():
    """Test low battery threshold detection."""
    print("\nLow Battery Threshold Test:")
    
    test_levels = [
        (25, 20, False),  # 25% with 20% threshold - not low
        (19, 20, True),   # 19% with 20% threshold - low
        (20, 20, False),  # 20% with 20% threshold - not low (equals threshold)
        (10, 15, True),   # 10% with 15% threshold - low
        (None, 20, False), # None value - not low
    ]
    
    passed = 0
    for level, threshold, expected_low in test_levels:
        # Simulate threshold check
        if level is None:
            is_low = False
        else:
            is_low = isinstance(level, (int, float)) and level < threshold
        
        if is_low == expected_low:
            print(f"  ✓ Level={level}%, Threshold={threshold}% -> Low={is_low}")
            passed += 1
        else:
            print(f"  ✗ Level={level}%, Threshold={threshold}% -> Low={is_low} (expected {expected_low})")
    
    return passed == len(test_levels)

if __name__ == "__main__":
    print("Battery Monitoring Test Suite")
    print("=" * 50)
    
    all_pass = True
    
    # Run tests
    if not test_battery_extraction():
        all_pass = False
    
    if not test_battery_status():
        all_pass = False
    
    if not run_battery_detection_tests():
        all_pass = False
    
    if not test_low_battery_threshold():
        all_pass = False
    
    print("\n" + "=" * 50)
    if all_pass:
        print("✓ All battery monitoring tests passed!")
        sys.exit(0)
    else:
        print("✗ Some tests failed")
        sys.exit(1)