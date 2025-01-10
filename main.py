from phew import access_point, connect_to_wifi, is_connected_to_wifi, dns, server
from phew.template import render_template
from led import led
from mqtt import mqtt
import json
import machine
import os
import utime
import _thread

AP_NAME = "FriendLamp"
AP_DOMAIN = "friendlamp.net"
AP_TEMPLATE_PATH = "ap_templates"
APP_TEMPLATE_PATH = "app_templates"
WIFI_FILE = "wifi.json"
WIFI_MAX_ATTEMPTS = 3

def machine_reset():
    utime.sleep(1)
    print("Resetting...")
    machine.reset()

def setup_mode():
    print("Entering setup mode...")
    led.set_all((128,0,0))
    
    def ap_index(request):
        if request.headers.get("host").lower() != AP_DOMAIN.lower():
            return render_template(f"{AP_TEMPLATE_PATH}/redirect.html", domain = AP_DOMAIN.lower())

        return render_template(f"{AP_TEMPLATE_PATH}/index.html")

    def ap_configure(request):
        print("Saving wifi credentials...")

        with open(WIFI_FILE, "w") as f:
            json.dump(request.form, f)
            f.close()

        # Reboot from new thread after we have responded to the user.
        _thread.start_new_thread(machine_reset, ())
        return render_template(f"{AP_TEMPLATE_PATH}/configured.html", ssid = request.form["ssid"])
        
    def ap_catch_all(request):
        if request.headers.get("host") != AP_DOMAIN:
            return render_template(f"{AP_TEMPLATE_PATH}/redirect.html", domain = AP_DOMAIN)

        return "Not found.", 404

    server.add_route("/", handler = ap_index, methods = ["GET"])
    server.add_route("/configure", handler = ap_configure, methods = ["POST"])
    server.set_callback(ap_catch_all)

    ap = access_point(AP_NAME)
    ip = ap.ifconfig()[0]
    dns.run_catchall(ip)

def application_mode():
    try:
        print("Entering application mode.")
     
        led.load_color()
        led.init_mqtt()
        
        print("LED intialised")

        def app_index(request):
            return render_template(f"{APP_TEMPLATE_PATH}/index.html")
        
        def app_reset(request):
            # Deleting the WIFI configuration file will cause the device to reboot as
            # the access point and request new configuration.
            os.remove(WIFI_FILE)
            # Reboot from new thread after we have responded to the user.
            _thread.start_new_thread(machine_reset, ())
            return render_template(f"{APP_TEMPLATE_PATH}/reset.html", access_point_ssid = AP_NAME)

        def app_catch_all(request):
            return "Not found.", 404

        server.add_route("/", handler = app_index, methods = ["GET"])
        server.add_route("/reset", handler = app_reset, methods = ["GET"])
        # Add other routes for your application...
        server.set_callback(app_catch_all)
    except Exception as e:
        print(f"Caught {e} in application_mode - resetting")
        machine_reset()
    
# Set up
led.init_led()

# Figure out which mode to start up in...
try:
    
    os.stat(WIFI_FILE)

    # File was found, attempt to connect to wifi...
    with open(WIFI_FILE) as f:
        print("Reading wifi file")
        wifi_current_attempt = 1
        wifi_credentials = json.load(f)
        
        while (wifi_current_attempt < WIFI_MAX_ATTEMPTS):
            led.spin_rainbow(1)
            print("Attempting wifi connect")
            ip_address = connect_to_wifi(wifi_credentials["ssid"], wifi_credentials["password"])

            if is_connected_to_wifi():
                print(f"Connected to wifi, IP address {ip_address}")
                break
            else:
                wifi_current_attempt += 1
                
        if is_connected_to_wifi():
            application_mode()
        else:
            
            # Bad configuration, delete the credentials file, reboot
            # into setup mode to get new credentials from the user.
            print("Bad wifi connection!")
            print(wifi_credentials)
            os.remove(WIFI_FILE)
            machine_reset()

except Exception as e:
    print(f"Received exception in main {e}")
    # Either no wifi configuration file found, or something went wrong, 
    # so go into setup mode.
    setup_mode()

# Start the web server...
server.run()