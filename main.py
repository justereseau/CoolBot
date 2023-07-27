#!/home/lmaurice/CoolBot/venv/bin/python

import glob
import threading
from prometheus_client import Gauge, start_http_server
from http.server import BaseHTTPRequestHandler, HTTPServer
import simplejson
import subprocess


HEATER_PIN = 13
HEATER_INITIAL_VALUE = 30

global sensor_values
sensor_values = {}

global heater_status
heater_status = None

# Manage the HTTP requests:
class MyServer(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def do_GET(self):
        data = {
            "sensors": sensor_values,
            "heater": heater_status,
        }
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.send_header("Access-Control-Allow-Origin", "http://justereseau.ca")
        self.end_headers()
        self.wfile.write(bytes(str(data), "utf-8"))

        # else:
        #     print(self.headers["Content-Type"])

    def do_POST(self):
        # Get the POST data as string
        post_data = self.rfile.read(int(self.headers['Content-Length']))
        data = simplejson.loads(post_data)

        response = "Bad parameters"
        
        # Filter the data
        if "heater" in data:
            max_value = 100
            min_value = 0
            if data["heater"] > max_value:
                set_heater_state(max_value)
                response = "heater request too high, will set {}% instead.".format(max_value)
            elif data["heater"] < min_value:
                set_heater_state(min_value)
                response = "heater request too low, will set {}% instead.".format(min_value)
            else:
                set_heater_state(data["heater"])
                response = "heater request ok, will set {}%.".format(data["heater"])

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.send_header("Access-Control-Allow-Origin", "http://justereseau.ca")
        self.end_headers()
        self.wfile.write(bytes(response, "utf-8"))


# Used to create the server as a separate thread
def create_server():
    webServer = HTTPServer(('frigo-full.coloc.djls.space', 8001), MyServer)
    webServer.serve_forever()


# Create the Prometheus metrics
prom_temperature = Gauge('temperature', 'Temperature measured by a sensor, in Celsius', ['sensor_id', 'sensor_name'])
prom_heater = Gauge('sensor_heater', 'Current command of the sensor heater, in Percent')

sensor_names = {
    "28-031394971c15": "Sensor",  # 0
    "28-030494974d6b": "Blower",  # 1
    "28-031094970130": "Intake",  # 2
    "28-030594970a8e": "Water",   # 3
}


def read_temp(sensor: str):
    file = open(f"/sys/bus/w1/devices/{sensor}/temperature", "r")
    content = file.read()

    if content == "":
        print(f"Error reading sensor {sensor}")
        return

    temp = int(content) / 1000
    file.close()

    if sensor in sensor_names:
        name = sensor_names[sensor]
    else:
        name = ""

    sensor_values[sensor] = temp
    prom_temperature.labels(sensor, name).set(temp)


def sensor_subroutine():
    while True:
        sensors = glob.glob("/sys/bus/w1/devices/28-*/temperature")

        # Get the ID of each sensor
        sensors = [sensor.split("/")[5] for sensor in sensors]

        threads = []

        for sensor in sensors:
            threads.append(threading.Thread(target=read_temp, args=(sensor,), daemon=True))

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()


# send the PWM value to the heater
def set_heater_state(state: int):
    global heater_status
    heater_status = state
    subprocess.run(["gpio", "-g", "pwm", str(HEATER_PIN), str(state)])
    prom_heater.set(state)

# Setup the GPIO
subprocess.run(["gpio", "-g", "mode", str(HEATER_PIN), "PWM"])
subprocess.run(["gpio", "pwm-ms"])
subprocess.run(["gpio", "pwmc", "384"])
subprocess.run(["gpio", "pwmr", "100"])

set_heater_state(HEATER_INITIAL_VALUE)

if True:
    start_http_server(8000)
    threading.Thread(target=create_server).start()
    threading.Thread(target=sensor_subroutine).start()
    while True:
        pass

else:
    create_server()
