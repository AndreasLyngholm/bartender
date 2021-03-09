import time
import sys
import RPi.GPIO as GPIO
import json
import threading
import traceback

from drinks import drink_list, drink_options

GPIO.setmode(GPIO.BCM)

FLOW_RATE = 60.0/100.0

class Bartender(MenuDelegate): 
	def __init__(self):
		self.running = False

		# load the pump configuration from file
		self.pump_configuration = Bartender.readPumpConfiguration()
		for pump in self.pump_configuration.keys():
			GPIO.setup(self.pump_configuration[pump]["pin"], GPIO.OUT, initial=GPIO.HIGH)

		print "Done initializing"

	@staticmethod
	def readPumpConfiguration():
		return json.load(open('pump_config.json'))

	@staticmethod
	def writePumpConfiguration(configuration):
		with open("pump_config.json", "w") as jsonFile:
			json.dump(configuration, jsonFile)

	def buildMenu(self, drink_list, drink_options):
		# create a new main menu
		m = Menu("Main Menu")

		# add drink options
		drink_opts = []
		for d in drink_list:
			drink_opts.append(MenuItem('drink', d["name"], {"ingredients": d["ingredients"]}))

		configuration_menu = Menu("Configure")

		# add pump configuration options
		pump_opts = []
		for p in sorted(self.pump_configuration.keys()):
			config = Menu(self.pump_configuration[p]["name"])
			# add fluid options for each pump
			for opt in drink_options:
				# star the selected option
				selected = "*" if opt["value"] == self.pump_configuration[p]["value"] else ""
				config.addOption(MenuItem('pump_selection', opt["name"], {"key": p, "value": opt["value"], "name": opt["name"]}))
			# add a back button so the user can return without modifying
			config.addOption(Back("Back"))
			config.setParent(configuration_menu)
			pump_opts.append(config)

		# add pump menus to the configuration menu
		configuration_menu.addOptions(pump_opts)
		# add a back button to the configuration menu
		configuration_menu.addOption(Back("Back"))
		# adds an option that cleans all pumps to the configuration menu
		configuration_menu.addOption(MenuItem('clean', 'Clean'))
		configuration_menu.setParent(m)

		m.addOptions(drink_opts)
		m.addOption(configuration_menu)
		# create a menu context
		self.menuContext = MenuContext(m, self)

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

	def selectConfigurations(self, menu):
		"""
		Adds a selection star to the pump configuration option
		"""
		for i in menu.options:
			if (i.type == "pump_selection"):
				key = i.attributes["key"]
				if (self.pump_configuration[key]["value"] == i.attributes["value"]):
					i.name = "%s %s" % (i.attributes["name"], "*")
				else:
					i.name = i.attributes["name"]
			elif (i.type == "menu"):
				self.selectConfigurations(i)

	def prepareForRender(self, menu):
		self.filterDrinks(menu)
		self.selectConfigurations(menu)
		return True

	def menuItemClicked(self, menuItem):
		if (menuItem.type == "drink"):
			self.makeDrink(menuItem.name, menuItem.attributes["ingredients"])
			return True
		elif(menuItem.type == "clean"):
			self.clean()
			return True
		return False

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

	def displayMenuItem(self, menuItem):
		print menuItem.name

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

	def makeDrink(self, drink, ingredients):
		# cancel any button presses while the drink is being made
		# self.stopInterrupts()
		self.running = True

		# launch a thread to control lighting
		lightsThread = threading.Thread(target=self.cycleLights)
		lightsThread.start()

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

	def updateProgressBar(self, percent):
		print percent

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
