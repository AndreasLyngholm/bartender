import time
import sys
import json
import threading
import traceback
import RPi.GPIO as GPIO
from drinks import drink_list, drink_options

from flask import Flask, jsonify, request
app = Flask(__name__)

GPIO.setmode(GPIO.BCM)

pump_configuration = None
global running
running = False

def readPumpConfiguration():
	return json.load(open('pump_config.json'))

# def clean():
# 	waitTime = 20
# 	pumpThreads = []

# 	# cancel any button presses while the drink is being made
# 	# stopInterrupts()
# 	running = True

# 	for pump in pump_configuration.keys():
# 		pump_t = threading.Thread(target=pour, args=(pump_configuration[pump]["pin"], waitTime))
# 		pumpThreads.append(pump_t)

# 	# start the pump threads
# 	for thread in pumpThreads:
# 		thread.start()

# 	# start the progress bar
# 	progressBar(waitTime)

# 	# wait for threads to finish
# 	for thread in pumpThreads:
# 		thread.join()

# 	# show the main menu
# 	menuContext.showMenu()

# 	# sleep for a couple seconds to make sure the interrupts don't get triggered
# 	time.sleep(2);

# 	# reenable interrupts
# 	# startInterrupts()
# 	running = False

def pour(pin, waitTime):
	# GPIO.output(pin, GPIO.LOW)
	time.sleep(waitTime)
	# GPIO.output(pin, GPIO.HIGH)

def checkRunning():
	global running
	return running

def toggleRunning(waitTime = 0):
	time.sleep(waitTime)
	global running
	running = not running

@app.route('/')
def hello():
	return "Hello World!"

@app.route('/drinks')
def drinks():
	drinks = []
	for drink in drink_list:
		ingredients = drink["ingredients"]
		presentIng = 0
		for ing in ingredients.keys():
			for p in pump_configuration.keys():
				if (ing == pump_configuration[p]["value"]):
					presentIng += 1
		if (presentIng == len(ingredients.keys())): 
			drinks.append(drink)

	response = jsonify(drinks)
	response.headers.add('Access-Control-Allow-Origin', '*')
	return response

@app.route('/make')
def make():
	drink = request.args.get('drink')
	strength = float(request.args.get('strength'))

	if checkRunning():
		response = jsonify({"error": "Der bliver allerede lavet en drink! Vent venligst."})
		response.headers.add('Access-Control-Allow-Origin', '*')
		return response

	toggleRunning()

	ingredients = ""
	for d in drink_list:
		if drink == d['name']:
			ingredients = d['ingredients']
	
	if ingredients != '':
		# Parse the drink ingredients and spawn threads for pumps
		maxTime = 0
		pumpThreads = []
		for ing in ingredients.keys():
			for pump in pump_configuration.keys():
				if ing == pump_configuration[pump]["value"]:
					for option in drink_options:
						if option["value"] == ing:
							choice = option

					waitTime = ingredients[ing] * (strength if choice["type"] == "alcohol" else 1) * (60.0/pump_configuration[pump]["speed"])
					if (waitTime > maxTime):
						maxTime = waitTime
					pump_t = threading.Thread(target=pour, args=(pump_configuration[pump]["pin"], waitTime))
					pumpThreads.append(pump_t)

		threading.Thread(target=toggleRunning, args=[maxTime]).start()
		# start the pump threads
		for thread in pumpThreads:
			thread.start()

		# print("Making drink, please wait...")
		# start the progress bar
		# progressBar(maxTime)

		# wait for threads to finish
		# for thread in pumpThreads:
		# 	thread.join()
		response = jsonify({"drink": drink, "time": maxTime})
		response.headers.add('Access-Control-Allow-Origin', '*')
		return response

	else:
		response = jsonify({"error": "Denne drink kan ikke laves"})
		response.headers.add('Access-Control-Allow-Origin', '*')
		return response

if __name__ == '__main__':
	pump_configuration = readPumpConfiguration()
	running = False
	for pump in pump_configuration.keys():
		GPIO.setup(pump_configuration[pump]["pin"], GPIO.OUT, initial=GPIO.HIGH)
	app.run(host= '0.0.0.0', port=8080)