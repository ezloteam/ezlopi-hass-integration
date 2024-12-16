import logging
import asyncio
import json
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

    for json_item in json_data:
        if json_item["show"] == True:
            valueType = json_item["valueType"]
            scale = json_item["scale"] if("scale" in json_item) else None
            value = json_item["value"]
            itemId = json_item["_id"]
            deviceId = json_item["deviceId"]
            deviceName = getDeviceName(deviceId, connector)

            if valueType == 'bool':
                controlType = "switch"

                if value == True:
                    value = 'on'
                else:
                    value = 'off'

            elif valueType == 'int' or valueType == 'float' or valueType == 'token' or valueType == 'string' or valueType == 'dictionary' or valueType == 'temperature' or valueType == 'humidity':
                controlType = "sensor"
            else:
                continue


            element = {"name": json_item["name"], "id": json_item["_id"], "deviceId": json_item["deviceId"],
                       "type": controlType, "value": value, "deviceName": deviceName,
                       "hasSetter": json_item["hasSetter"], 'deviceClass': None, 'unitOfMeasurement': None}
            
            if(valueType in ['temperature', 'humidity']):
                element['deviceClass'] = valueType
            
            if(scale != None):
                if(scale == 'celsius'):
                    element['unitOfMeasurement'] = '°C'
                else:
                    element['unitOfMeasurement'] = scale
            
            if(valueType == 'humidity'):
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