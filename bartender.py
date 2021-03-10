import time
import sys
import json
import threading
import traceback
# import RPi.GPIO as GPIO

from flask import Flask, jsonify
app = Flask(__name__)

from drinks import drink_list, drink_options

# GPIO.setmode(GPIO.BCM)

class Bartender(): 
	# def __init__(self):
	# 	self.running = False

	# 	# load the pump configuration from file
	# 	self.pump_configuration = Bartender.readPumpConfiguration()
	# 	for pump in self.pump_configuration.keys():
	# 		GPIO.setup(self.pump_configuration[pump]["pin"], GPIO.OUT, initial=GPIO.HIGH)

	@staticmethod
	def readPumpConfiguration():
		return json.load(open('pump_config.json'))

	@staticmethod
	def writePumpConfiguration(configuration):
		with open("pump_config.json", "w") as jsonFile:
			json.dump(configuration, jsonFile)

	def filterDrinks(self, menu):
		"""
		Removes any drinks that can't be handled by the pump configuration
		"""
		for i in menu.options:
			if (i.type == "drink"):
				i.visible = False
				ingredients = i.attributes["ingredients"]
				presentIng = 0
				for ing in ingredients.keys():
					for p in self.pump_configuration.keys():
						if (ing == self.pump_configuration[p]["value"]):
							presentIng += 1
				if (presentIng == len(ingredients.keys())): 
					i.visible = True
			elif (i.type == "menu"):
				self.filterDrinks(i)

	def clean(self):
		waitTime = 20
		pumpThreads = []

		# cancel any button presses while the drink is being made
		# self.stopInterrupts()
		self.running = True

		for pump in self.pump_configuration.keys():
			pump_t = threading.Thread(target=self.pour, args=(self.pump_configuration[pump]["pin"], waitTime))
			pumpThreads.append(pump_t)

		# start the pump threads
		for thread in pumpThreads:
			thread.start()

		# start the progress bar
		self.progressBar(waitTime)

		# wait for threads to finish
		for thread in pumpThreads:
			thread.join()

		# show the main menu
		self.menuContext.showMenu()

		# sleep for a couple seconds to make sure the interrupts don't get triggered
		time.sleep(2);

		# reenable interrupts
		# self.startInterrupts()
		self.running = False

	def showDrinks(self, ):
		for drink in drink_list:
			print(drink['name'])

	def pour(self, pin, waitTime):
		GPIO.output(pin, GPIO.LOW)
		time.sleep(waitTime)
		GPIO.output(pin, GPIO.HIGH)

	def progressBar(self, waitTime):
		interval = waitTime / 100.0
		for x in range(1, 101):
			if x % 10 == 0:
				print("{}%".format(x))
			time.sleep(interval)

	def makeDrink(self, drink):
		# cancel any button presses while the drink is being made
		# self.stopInterrupts()
		self.running = True

		ingredients = ""
		for d in drink_list:
			if drink == d['name']:
				ingredients = d['ingredients']

		print(ingredients, "\n")
		
		if ingredients != '':
			# Parse the drink ingredients and spawn threads for pumps
			maxTime = 0
			pumpThreads = []
			for ing in ingredients.keys():
				for pump in self.pump_configuration.keys():
					if ing == self.pump_configuration[pump]["value"]:
						waitTime = ingredients[ing] * (60.0/self.pump_configuration[pump]["speed"])
						if (waitTime > maxTime):
							maxTime = waitTime
						pump_t = threading.Thread(target=self.pour, args=(self.pump_configuration[pump]["pin"], waitTime))
						pumpThreads.append(pump_t)

			# start the pump threads
			for thread in pumpThreads:
				thread.start()

			print("Making drink, please wait...")
			# start the progress bar
			self.progressBar(maxTime)

			# wait for threads to finish
			for thread in pumpThreads:
				thread.join()

			print(drink, "was finished! Enjoy the drink!\n")

			# reenable interrupts
			# self.startInterrupts()
			self.running = False
		else:
			print("The drink does not exist\n")

	# def run(self):
	# 	# main loop
	# 	try:  
	# 		while True:
	# 			print("Select a drink for the list below\n")
	# 			self.showDrinks()
	# 			drink = input("\n\nSelect a drink.\n")
	# 			self.makeDrink(drink)

	# 	except KeyboardInterrupt:  
	# 		GPIO.cleanup()       # clean up GPIO on CTRL+C exit  
	# 	GPIO.cleanup()           # clean up GPIO on normal exit 

	# 	traceback.print_exc()


@app.route('/')
def hello():
	return "Hello World!"

@app.route('/drinks')
def drinks():
	response = jsonify(drink_list)
	response.headers.add('Access-Control-Allow-Origin', '*')
	return response

if __name__ == '__main__':
	bartender = Bartender()
	app.run(host= '0.0.0.0', port=8080)