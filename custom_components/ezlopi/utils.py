import logging
import asyncio
import json
from .device_types import detect_device_platform, get_additional_entities

_LOGGER = logging.getLogger(__name__)

import subprocess

def get_items(connector):
    return connector.items

def get_devices(connector):
    return connector.devices

def set_item_value_request(id, value):
    return {
        "id": "_ID_",
        "method": "hub.item.value.set",
        "call": "hub.item.value.set",
        "params": {
            "value": value,
            "_id": id
        }
    }

def system_logging_param():
    return {
            "id": "_ID_",
            "method": "hub.log.set",
            "params": {
                "enable": False,
                "severity": "INFO"
            }
        }

def set_item_value ():
    return{
            "id": "_ID_",
            "method": "hub.item.value.set",
            "params": ""
        }

def get_devices_info ():
    return [
            {
                "method": "hub.items.list",
                "id": "_ID_",
                "params": {}
            },
            {
                "method": "hub.devices.list",
                "id": "_ID_",
                "params": {}
            }
        ]

def get_login_params ():
    return {
            "method": "hub.offline.login.ui",
            "id": "_ID_",
            "params": {
            }
        }

def getDeviceName(id, connector):
    json_data = get_devices(connector)
    for json_item in json_data:
        if json_item["_id"] == id:
            return json_item["name"]

def getItemsData(connector, id=''):
    result = []
    json_data = get_items(connector)

    if json_data == None:
        return

    # Get device metadata if available
    devices_data = get_devices(connector) or []
    device_metadata = {}
    for device in devices_data:
        device_id = device.get("_id")
        if device_id:
            device_metadata[device_id] = {
                "deviceType": device.get("deviceTypeId"),
                "category": device.get("category"),
                "subcategory": device.get("subcategory"),
                "armed": device.get("armed", False)
            }

    for json_item in json_data:
        if json_item["show"] == True:
            valueType = json_item["valueType"]
            scale = json_item["scale"] if("scale" in json_item) else None
            value = json_item["value"]
            itemId = json_item["_id"]
            deviceId = json_item["deviceId"]
            deviceName = getDeviceName(deviceId, connector)

            # Build device info for detection
            device_info = {
                "name": json_item["name"],
                "deviceName": deviceName,
                "valueType": valueType,
                "hasSetter": json_item["hasSetter"],
                "scale": scale,
                "value": value
            }
            
            # Add device metadata if available
            if deviceId in device_metadata:
                device_info.update(device_metadata[deviceId])
            
            # Use enhanced device detection
            detection_result = detect_device_platform(device_info)
            controlType = detection_result["platform"]
            deviceClass = detection_result.get("device_class")
            
            # Handle value conversion based on platform
            if controlType == "switch" and valueType == 'bool':
                value = 'on' if value else 'off'
            elif controlType == "binary_sensor" and valueType == 'bool':
                # Keep boolean for binary sensors
                pass
            elif controlType == "light" and valueType in ['int', 'float']:
                # Keep numeric value for brightness
                pass

            element = {
                "name": json_item["name"], 
                "id": json_item["_id"], 
                "deviceId": json_item["deviceId"],
                "type": controlType, 
                "value": value, 
                "deviceName": deviceName,
                "hasSetter": json_item["hasSetter"], 
                "deviceClass": deviceClass, 
                "unitOfMeasurement": None
            }
            
            # Add metadata to element
            if deviceId in device_metadata:
                element["category"] = device_metadata[deviceId].get("category")
                element["subcategory"] = device_metadata[deviceId].get("subcategory")
                element["deviceType"] = device_metadata[deviceId].get("deviceType")
                element["armed"] = device_metadata[deviceId].get("armed")
            
            # Handle unit of measurement
            if valueType in ['temperature', 'humidity'] and not deviceClass:
                element['deviceClass'] = valueType
            
            # Special handling for battery sensors
            if deviceClass == 'battery':
                element['unitOfMeasurement'] = '%'
                # Ensure battery value is numeric
                if isinstance(value, (int, float)):
                    element['value'] = int(value)
            
            if scale != None:
                if scale == 'celsius':
                    element['unitOfMeasurement'] = '°C'
                elif scale == 'fahrenheit':
                    element['unitOfMeasurement'] = '°F'
                elif scale == 'percent':
                    element['unitOfMeasurement'] = '%'
                else:
                    element['unitOfMeasurement'] = scale
            
            if valueType == 'humidity' and not element['unitOfMeasurement']:
                element['unitOfMeasurement'] = '%'

            if itemId == id:
                return element

            if (id == ''):
                result.append(element)

    return result


async def get_devices_from_platform(api):
    items = getItemsData(api)
    _LOGGER.info("items:{}".format(items))

    for i in range(0, 100):
        if items == None:
            await asyncio.sleep(1)
            items = getItemsData(api)
        else:
            break

    return items

async def get_device_data(device_id, api):
    json_data = getItemsData(api, device_id)
    return json_data["value"]

async def ping_host(ip_address):
    try:
        response = subprocess.run(
            ["ping", "-c", "3", "-W", "1", ip_address],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return response.returncode == 0
    except Exception as e:
        _LOGGER.error(f"Error during ping: {e}")
        return False

def extract_battery_info(devices):
    """Extract battery information for all devices.
    
    Returns dict mapping device_id to battery info.
    """
    battery_info = {}
    
    for device in devices:
        device_id = device.get("deviceId")
        if not device_id:
            continue
            
        # Check if this is a battery sensor
        if device.get("deviceClass") == "battery":
            parent_device_id = device.get("deviceId")
            if parent_device_id not in battery_info:
                battery_info[parent_device_id] = {
                    "battery_level": device.get("value", 0),
                    "battery_item_id": device.get("id"),
                    "has_battery": True
                }
    
    return battery_info

def get_device_battery_level(device_id, connector):
    """Get battery level for a specific device."""
    devices = getItemsData(connector)
    if not devices:
        return None
        
    for device in devices:
        if (device.get("deviceId") == device_id and 
            device.get("deviceClass") == "battery"):
            return device.get("value")
    
    return None

def should_create_low_battery_sensor(battery_level, threshold=20):
    """Check if a low battery sensor should be created."""
    if battery_level is None:
        return False
    return isinstance(battery_level, (int, float)) and battery_level < threshold