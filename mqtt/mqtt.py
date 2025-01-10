from umqtt.simple import MQTTClient
import network
import asyncio
import json
import time

MQTT_FILE="mqtt.json"

mqtt_client = None
mqtt_client_id = None
mqtt_config = None

def mqtt_init(callback=None):
    global mqtt_client, mqtt_config, mqtt_client_id
    
    with open(MQTT_FILE) as f:
        mqtt_config = json.load(f)

    wlan = network.WLAN(network.STA_IF)

    mqtt_client_id=wlan.config('mac').hex()

    # Initialize our MQTTClient and connect to the MQTT server
    mqtt_client = MQTTClient(
            client_id=mqtt_client_id,
            server=mqtt_config["mqtt_host"],
            user=mqtt_config["mqtt_username"],
            password=mqtt_config["mqtt_password"])
    
    if callback:
        mqtt_client.set_callback(callback)
        
    print("MQTT setup complete - starting async process")
    
    asyncio.run(mqtt_listen())
    
    print("MQTT listener started")


def mqtt_send(message):
    if mqtt_client:
        payload = {
            "id":mqtt_client_id,
            "message":message
            }
        msg = json.dumps(payload)
        print(f"MQTT sending {msg}")
        mqtt_client.publish(mqtt_config["mqtt_topic"], msg,retain=True)
    else:
        print("No MQTT Client")

async def mqtt_listen():
    while True: 
        mqtt_client.connect()

        print("MQTT client connected")

        mqtt_client.subscribe(mqtt_config["mqtt_topic"])

        print("MQTT client subscribed")
        
        try:
            while True:
                print("Waiting for message")
                mqtt_client.wait_msg()
        except Exception as e:
            print(f"Exception from mqtt: {e}")
            mqtt_client.disconnect()
                
    
