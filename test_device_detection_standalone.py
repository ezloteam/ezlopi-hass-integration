#!/usr/bin/env python3
"""Standalone test for device type detection without Home Assistant dependencies."""

# Copy the detection logic here to test without imports
import logging

_LOGGER = logging.getLogger(__name__)

# Simplified version of device type detection for testing
DEVICE_TYPE_MAP = {
    "sensor.motion": {"platform": "binary_sensor", "device_class": "motion"},
    "doorlock": {"platform": "lock", "device_class": "lock"},
    "dimmer.outlet": {"platform": "light", "device_class": "light"},
    "switch.outlet": {"platform": "switch", "device_class": "outlet"},
    "switch.inwall": {"platform": "switch", "device_class": "switch"},
    "thermostat": {"platform": "climate", "device_class": "thermostat"},
    "transmitter.ir": {"platform": "remote", "device_class": "remote"},
}

ITEM_NAME_PATTERNS = {
    "motion": {"platform": "binary_sensor", "device_class": "motion"},
    "door": {"platform": "binary_sensor", "device_class": "door"},
    "window": {"platform": "binary_sensor", "device_class": "window"},
    "dimmer": {"platform": "light", "device_class": "light"},
    "brightness": {"platform": "light", "device_class": "light"},
    "battery": {"platform": "sensor", "device_class": "battery"},
    "temperature": {"platform": "sensor", "device_class": "temperature"},
    "humidity": {"platform": "sensor", "device_class": "humidity"},
}

def detect_device_platform(device_info):
    """Test version of platform detection."""
    
    # 1. Check explicit device type
    device_type = device_info.get("deviceType")
    if device_type and device_type in DEVICE_TYPE_MAP:
        return DEVICE_TYPE_MAP[device_type].copy()
    
    # 2. Check name patterns
    name = device_info.get("name", "").lower()
    for pattern, mapping in ITEM_NAME_PATTERNS.items():
        if pattern in name:
            return mapping.copy()
    
    # 3. Check value type
    value_type = device_info.get("valueType")
    has_setter = device_info.get("hasSetter", False)
    
    if value_type == "bool":
        if has_setter:
            return {"platform": "switch", "device_class": "switch"}
        else:
            return {"platform": "binary_sensor", "device_class": None}
    elif value_type == "temperature":
        return {"platform": "sensor", "device_class": "temperature"}
    elif value_type == "humidity":
        return {"platform": "sensor", "device_class": "humidity"}
    elif value_type in ["int", "float"]:
        if has_setter and device_info.get("scale") == "percent":
            return {"platform": "light", "device_class": "light"}
        return {"platform": "sensor", "device_class": None}
    
    # Default
    return {"platform": "sensor", "device_class": None}

# Test cases
test_cases = [
    {
        "name": "Motion Sensor",
        "input": {"name": "Living Room Motion", "deviceType": "sensor.motion", "valueType": "bool", "hasSetter": False},
        "expected": {"platform": "binary_sensor", "device_class": "motion"}
    },
    {
        "name": "Door Lock",
        "input": {"name": "Front Door", "deviceType": "doorlock", "valueType": "token", "hasSetter": True},
        "expected": {"platform": "lock", "device_class": "lock"}
    },
    {
        "name": "Dimmer",
        "input": {"name": "Living Room Light", "deviceType": "dimmer.outlet", "valueType": "int", "hasSetter": True},
        "expected": {"platform": "light", "device_class": "light"}
    },
    {
        "name": "Switch",
        "input": {"name": "Power Switch", "valueType": "bool", "hasSetter": True},
        "expected": {"platform": "switch", "device_class": "switch"}
    },
    {
        "name": "Temperature Sensor",
        "input": {"name": "Room Temp", "valueType": "temperature", "hasSetter": False},
        "expected": {"platform": "sensor", "device_class": "temperature"}
    },
    {
        "name": "Motion by Name",
        "input": {"name": "motion_hallway", "valueType": "bool", "hasSetter": False},
        "expected": {"platform": "binary_sensor", "device_class": "motion"}
    },
    {
        "name": "Dimmer by Percent",
        "input": {"name": "brightness", "valueType": "int", "scale": "percent", "hasSetter": True},
        "expected": {"platform": "light", "device_class": "light"}
    },
    {
        "name": "Battery Sensor",
        "input": {"name": "battery_level", "valueType": "int", "scale": "percent", "hasSetter": False},
        "expected": {"platform": "sensor", "device_class": "battery"}
    },
]

def run_tests():
    """Run test cases."""
    print("=" * 60)
    print("Device Type Detection Test Results")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        result = detect_device_platform(test["input"])
        expected = test["expected"]
        
        success = (result.get("platform") == expected["platform"] and 
                  result.get("device_class") == expected["device_class"])
        
        status = "✓" if success else "✗"
        if success:
            passed += 1
        else:
            failed += 1
        
        print(f"\n{status} {test['name']}")
        print(f"   Input: {test['input']}")
        print(f"   Expected: {expected}")
        print(f"   Got:      {result}")
        
        if not success:
            print("   *** MISMATCH ***")
    
    print("\n" + "=" * 60)
    print(f"Summary: {passed}/{len(test_cases)} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0

if __name__ == "__main__":
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)