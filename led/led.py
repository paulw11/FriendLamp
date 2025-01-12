import machine,neopixel
from machine import Timer
from machine import Pin
import time
import math
import random
import json
import os
from mqtt import mqtt

LED_FILE="led.json"

DIM_DELAY=30000 # Dim after 30 seconds
KEEPALIVE_INTERVAL=300000 # Send keepalive after 5 minutes

np = neopixel.NeoPixel(machine.Pin(27), 12)
touch = machine.Pin(28, Pin.IN, Pin.PULL_UP)

number_of_pixels = 12

dim_timer = Timer(-1)
keepalive_timer = Timer(-1)

current_color=(0,0,0)

## Interrupt
        
def touch_callback(pin):
    current=current_color
    while pin.value():
        new_color = random_color()
        shift(current,new_color)
        current = new_color
        time.sleep(2)
    set_current(new_color,publish=True)
        
## LED operations

def clear(write=True):
    set_all((0,0,0),write)

def set_all(tuple, write=True, brightness=1):
    
    targetColor = (int(tuple[0]*brightness),int(tuple[1]*brightness),int(tuple[2]*brightness))
    
    for pixel in range(number_of_pixels):
        np[pixel] = targetColor
    if write:
        np.write()
    
def spin(tuple):
     for pixel in range(number_of_pixels):
         setAll((0,128,0),False)
         np[pixel]=tuple
         np.write()
         time.sleep(0.01)
         
def display_array(array,offset):
    index = offset
    n = len(array)
    for pixel in range(number_of_pixels):
        np[pixel]=array[index % n]
        index+=1
    np.write()
    
async def spin_rainbow(times,speed=0.02):
    rainbow = generate_rainbow_steps(number_of_pixels)
    for iteration in range(times):
        for offset in range(number_of_pixels):
            display_array(rainbow,offset)
            time.sleep(speed)

def shift(fromColor, toColor,brightness=1):
    rSpan = toColor[0]-fromColor[0]
    gSpan = toColor[1]-fromColor[1]
    bSpan = toColor[2]-fromColor[2]
    
    steps = max(max(abs(rSpan),abs(gSpan)),abs(bSpan))
 
    
    if steps:
    
        rStep = rSpan/steps
        gStep = gSpan/steps
        bStep = bSpan/steps
        
        red = fromColor[0]
        green = fromColor[1]
        blue = fromColor[2]
        
        
        for step in range(steps):
            set_all((int(red),int(green),int(blue)),brightness)
            red = red+rStep
            green = green+gStep
            blue = blue+bStep
            time.sleep(0.01)

    
    set_all(toColor)
        
## Utilitity

def generate_rainbow_steps(steps, brightness=1):
    rainbow_colors = []
    for i in range(steps):
        hue = i / steps  # Normalize the hue to the range [0, 1)
        angle = hue * 2 * math.pi  # Convert to angle in radians

        # Generate RGB components based on a sine wave
        r = int((math.sin(angle) + 1) * 127.5 * brightness)
        g = int((math.sin(angle + 2 * math.pi / 3) + 1) * 127.5 * brightness)
        b = int((math.sin(angle + 4 * math.pi / 3) + 1) * 127.5 * brightness)

        rainbow_colors.append((r, g, b))
    return rainbow_colors

def random_color():
    red = random.randrange(256)
    green = random.randrange(256-red)
    blue = 255-red-green
    return (red,green,blue)

## Initialisation

def init_led():
    clear()
    touch.irq(trigger=Pin.IRQ_RISING, handler=touch_callback)
    keepalive_timer.init(mode=Timer.PERIODIC, period = KEEPALIVE_INTERVAL, callback = keepalive_timer_callback)
    
def init_mqtt():
    mqtt.mqtt_init(mqtt_callback)
    
## State management
    
def set_current(color, save=True, publish=False, use_shift=False):
    global current_color, dim_timer
    if use_shift:
        shift(current_color,color)
    else:
        set_all(color)
    current_color=color
    if save:
        save_color(color,publish)
        
    dim_timer.deinit()
    dim_timer.init(mode=Timer.ONE_SHOT, period = DIM_DELAY, callback = dim_timer_callback)
        
def dim_timer_callback(timer):
    timer.deinit()
    set_all(current_color,brightness=0.2)
    

def keepalive_timer_callback(timer):
    global current_color
    print("Sending keepalive")
    mqtt.mqtt_send(color_object(current_color))

def color_object(color):
    return {
            "red":color[0],
            "green":color[1],
            "blue":color[2]
            }
    

def save_color(color,publish=True):
    with open(LED_FILE, "w") as f:
        obj = color_object(color)
        json.dump(color, f)
        f.close()
        if publish:
            mqtt.mqtt_send(obj)

    
def load_color():
    
    # See if we can get saved color
    try:
    
        os.stat(LED_FILE)

        # File was found, attempt to set color
        with open(LED_FILE) as f:
            color = json.load(f)
            set_current((color["red"],color["green"],color["blue"]),save=False)
    except Exception as e:
        print(e)
        # No file or file didn't load
        set_current((0,128,0), save=True)
        

## MQTT Callback
        
def mqtt_callback(topic,message):
    try:
        print(f"Received {message} on {topic}")
        incoming=json.loads(message)
        id = incoming['id']
        if not id == mqtt.mqtt_client_id:
            print("message is not from us")
            color = incoming["message"]
            set_current((color["red"],color["green"],color["blue"]),use_shift=True)
    except Exception as e:
        print(e)
        

