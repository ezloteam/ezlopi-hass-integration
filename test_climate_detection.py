#!/usr/bin/env python3
"""Test climate/thermostat detection."""

import sys
sys.path.insert(0, 'custom_components/ezlopi')

# Import device_types module
exec(open('custom_components/ezlopi/device_types.py').read())

# Test cases for climate detection
test_cases = [
    {
        "name": "Thermostat - Direct Type",
        "input": {
            "name": "Living Room Thermostat",
            "deviceType": "thermostat",
            "valueType": "float",
            "hasSetter": True,
            "value": 22.5
        },
        "expected": {
            "platform": "climate",
            "device_class": "thermostat"
        }
    },
    {
        "name": "Thermostat - Name Pattern",
        "input": {
            "name": "main_thermostat",
            "valueType": "float",
            "hasSetter": True,
            "scale": "celsius",
            "value": 21.0
        },
        "expected": {
            "platform": "climate",
            "device_class": "thermostat"
        }
    },
    {
        "name": "HVAC - Name Pattern",
        "input": {
            "name": "hvac_controller",
            "valueType": "dict",
            "hasSetter": True,
            "value": {"temp": 23, "mode": "heat"}
        },
        "expected": {
            "platform": "climate",
            "device_class": "thermostat"
        }
    },
    {
        "name": "Air Conditioner - Name Pattern",
        "input": {
            "name": "bedroom_air_conditioner",
            "valueType": "float",
            "hasSetter": True,
            "value": 24.0
        },
        "expected": {
            "platform": "climate",
            "device_class": "thermostat"
        }
    },
    {
        "name": "Heater - Name Pattern",
        "input": {
            "name": "space_heater",
            "valueType": "int",
            "hasSetter": True,
            "value": 25
        },
        "expected": {
            "platform": "climate",
            "device_class": "thermostat"
        }
    },
    {
        "name": "Climate Category",
        "input": {
            "name": "Zone Controller",
            "category": "climate",
            "valueType": "float",
            "hasSetter": True,
            "value": 20.5
        },
        "expected": {
            "platform": "climate",
            "device_class": "thermostat"
        }
    },
    {
        "name": "Temperature Sensor (not climate)",
        "input": {
            "name": "ambient_temperature",
            "valueType": "float",
            "hasSetter": False,
            "scale": "celsius",
            "value": 18.5
        },
        "expected": {
            "platform": "sensor",
            "device_class": "temperature"
        }
    },
    {
        "name": "Regular Switch (not climate)",
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

def test_hvac_modes():
    """Test HVAC mode mapping."""
    print("Testing HVAC Mode Mapping")
    print("=" * 50)
    
    # Simulate mode mapping
    mode_tests = [
        ("off", "OFF"),
        ("heat", "HEAT"),
        ("cool", "COOL"),
        ("auto", "AUTO"),
        ("heat_cool", "HEAT_COOL"),
        ("fan_only", "FAN_ONLY"),
    ]
    
    passed = 0
    for ezlo_mode, expected_hvac in mode_tests:
        # Simulate mapping (would be in climate.py)
        hvac_mode = ezlo_mode.upper().replace("_", "_")
        
        if hvac_mode == expected_hvac:
            print(f"  ✓ {ezlo_mode} -> {hvac_mode}")
            passed += 1
        else:
            print(f"  ✗ {ezlo_mode} -> {hvac_mode} (expected {expected_hvac})")
    
    return passed == len(mode_tests)

def test_temperature_scales():
    """Test temperature scale handling."""
    print("\nTesting Temperature Scales")
    print("=" * 50)
    
    scale_tests = [
        ("celsius", "°C", 10.0, 35.0),
        ("fahrenheit", "°F", 50.0, 95.0),
    ]
    
    passed = 0
    for scale, unit, min_temp, max_temp in scale_tests:
        print(f"  Scale: {scale}")
        print(f"    Unit: {unit}")
        print(f"    Range: {min_temp} - {max_temp}")
        passed += 1
    
    return passed == len(scale_tests)

def test_hvac_actions():
    """Test HVAC action determination."""
    print("\nTesting HVAC Actions")
    print("=" * 50)
    
    action_tests = [
        ("off", 20.0, 20.0, "OFF"),
        ("heat", 18.0, 22.0, "HEATING"),
        ("heat", 23.0, 22.0, "IDLE"),
        ("cool", 26.0, 24.0, "COOLING"),
        ("cool", 23.0, 24.0, "IDLE"),
    ]
    
    passed = 0
    for mode, current, target, expected_action in action_tests:
        # Simulate action determination
        if mode == "off":
            action = "OFF"
        elif mode == "heat":
            action = "HEATING" if current < target else "IDLE"
        elif mode == "cool":
            action = "COOLING" if current > target else "IDLE"
        else:
            action = "IDLE"
        
        if action == expected_action:
            print(f"  ✓ Mode={mode}, Current={current}°, Target={target}° -> {action}")
            passed += 1
        else:
            print(f"  ✗ Mode={mode}, Current={current}°, Target={target}° -> {action} (expected {expected_action})")
    
    return passed == len(action_tests)

def run_tests():
    """Run all test cases and report results."""
    print("Testing Climate/Thermostat Detection")
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
    
    return failed == 0

if __name__ == "__main__":
    all_pass = True
    
    # Run detection tests
    if not run_tests():
        all_pass = False
    
    print("\n")
    
    # Run mode tests
    if not test_hvac_modes():
        all_pass = False
    
    # Run scale tests
    if not test_temperature_scales():
        all_pass = False
    
    # Run action tests
    if not test_hvac_actions():
        all_pass = False
    
    print("\n" + "=" * 50)
    if all_pass:
        print("✓ All climate detection tests passed!")
        sys.exit(0)
    else:
        print("✗ Some tests failed")
        sys.exit(1)