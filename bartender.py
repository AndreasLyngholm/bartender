import time
import sys
import RPi.GPIO as GPIO
import json
import threading
import traceback

from drinks import drink_list, drink_options

GPIO.setmode(GPIO.BCM)

FLOW_RATE = 60.0/100.0

class Bartender(): 
	def __init__(self):
		self.running = False

		# load the pump configuration from file
		self.pump_configuration = Bartender.readPumpConfiguration()
		for pump in self.pump_configuration.keys():
			GPIO.setup(self.pump_configuration[pump]["pin"], GPIO.OUT, initial=GPIO.HIGH)

		print("Done initializing")

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
			self.led.clear_display()
			self.updateProgressBar(x, y=35)
			self.led.display()
			time.sleep(interval)

	def makeDrink(self, drink):
		# cancel any button presses while the drink is being made
		# self.stopInterrupts()
		self.running = True

		ingredients = ""
		for d in drink_list:
			if drink == d['name']:
				ingredients = d['ingredients']
		
		if ingredients != '':


			# Parse the drink ingredients and spawn threads for pumps
			maxTime = 0
			pumpThreads = []
			for ing in ingredients.keys():
				for pump in self.pump_configuration.keys():
					if ing == self.pump_configuration[pump]["value"]:
						waitTime = ingredients[ing] * FLOW_RATE
						if (waitTime > maxTime):
							maxTime = waitTime
						pump_t = threading.Thread(target=self.pour, args=(self.pump_configuration[pump]["pin"], waitTime))
						pumpThreads.append(pump_t)

			# start the pump threads
			for thread in pumpThreads:
				thread.start()

			# start the progress bar
			self.progressBar(maxTime)

			# wait for threads to finish
			for thread in pumpThreads:
				thread.join()

			# sleep for a couple seconds to make sure the interrupts don't get triggered
			time.sleep(2);

			# reenable interrupts
			# self.startInterrupts()
			self.running = False
		else:
			print("The drink does not exist")

	def updateProgressBar(self, percent):
		print(percent)

	def run(self):
		self.startInterrupts()
		# main loop
		try:  
			while True:
				time.sleep(0.1)
		  
		except KeyboardInterrupt:  
			GPIO.cleanup()       # clean up GPIO on CTRL+C exit  
		GPIO.cleanup()           # clean up GPIO on normal exit 

		traceback.print_exc()

bartender = Bartender()
bartender.buildMenu(drink_list, drink_options)
bartender.run()
