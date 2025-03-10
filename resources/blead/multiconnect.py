from bluepy import btle
import time
import logging
import globals
import struct

class Connector():
	def __init__(self,mac):
		self.name = 'connector'
		self.mac = mac
		self.conn = ''
		self.isconnected = False

	def connect(self,retry=3,type='public'):
		logging.debug('CONNECTOR------Connecting : '+str(self.mac) + ' with bluetooth ' + str(globals.IFACE_DEVICE))
		i=0
		timeout = time.time() + 15
		while time.time()<timeout:
			i = i + 1
			try:
				globals.PENDING_ACTION = True
				globals.PENDING_TIME = int(time.time())
				if type == 'public':
					connection = btle.Peripheral(self.mac,iface=globals.IFACE_DEVICE)
					self.isconnected = True
					break
				else:
					connection = btle.Peripheral(self.mac,addrType = btle.ADDR_TYPE_RANDOM,iface=globals.IFACE_DEVICE)
					self.isconnected = True
					break
			except Exception as e:
				logging.debug('CONNECTOR------'+str(e) + ' attempt ' + str(i) )
				if i >= retry:
					self.isconnected = False
					if self.mac in globals.KEEPED_CONNECTION:
						del globals.KEEPED_CONNECTION[self.mac]
					logging.debug('CONNECTOR------Issue connecting to : '+str(self.mac) + ' with bluetooth ' + str(globals.IFACE_DEVICE) + ' the device is busy or too far')
					globals.PENDING_ACTION = False
					globals.PENDING_TIME = int(time.time())
					return
				time.sleep(1)
		if self.isconnected:
			self.conn = connection
			globals.PENDING_ACTION = False
			globals.PENDING_TIME = int(time.time())
			logging.debug('CONNECTOR------Connected... ' + str(self.mac))
		return

	def disconnect(self,force=False):
		globals.PENDING_ACTION = False
		globals.PENDING_TIME = int(time.time())
		if self.mac.upper() in globals.KNOWN_DEVICES and globals.KNOWN_DEVICES[self.mac.upper()]['islocked'] == 1 and globals.KNOWN_DEVICES[self.mac.upper()]['emitterallowed'] in [globals.daemonname,'all'] and force==False:
			logging.debug('CONNECTOR------Not Disconnecting I\'m configured to keep connection with this device... ' + str(self.mac))
			globals.KEEPED_CONNECTION[self.mac]=self
			return
		logging.debug('CONNECTOR------Disconnecting... ' + str(self.mac))
		i=0
		while True:
			i = i + 1
			try:
				self.conn.disconnect()
				break
			except Exception as e:
				if 'str' in str(e) and 'has no attribute' in str(e):
					logging.debug('CONNECTOR------'+str(e))
					self.isconnected = False
					if self.mac in globals.KEEPED_CONNECTION:
						del globals.KEEPED_CONNECTION[self.mac]
					return
				logging.debug('CONNECTOR------'+str(e) + ' attempt ' + str(i) )
				if i >= 2:
					self.isconnected = False
					if self.mac in globals.KEEPED_CONNECTION:
						del globals.KEEPED_CONNECTION[self.mac]
					return
		if self.mac in globals.KEEPED_CONNECTION:
			del globals.KEEPED_CONNECTION[self.mac]
		self.isconnected = False
		logging.debug('CONNECTOR------Disconnected...'+ str(self.mac))

	def readCharacteristic(self,handle,retry=1,type='public'):
		logging.debug(f'CONNECTOR------Reading Characteristic {handle}...'+ str(self.mac))
		ireadCharacteristic=0
		while True:
			ireadCharacteristic = ireadCharacteristic + 1
			try:
				result = self.conn.readCharacteristic(int(handle,16))
				break
			except Exception as e:
				logging.debug(str(e))
				if ireadCharacteristic >= retry:
					self.disconnect(True)
					if self.mac in globals.KEEPED_CONNECTION:
						del globals.KEEPED_CONNECTION[self.mac]
					return False
				logging.debug('CONNECTOR------Retry connection '+ str(self.mac))
				self.connect(type=type)
		logging.debug(f'CONNECTOR------Characteristic {handle} Readen: {result} ... ' + str(self.mac))
		return result

	def writeCharacteristic(self,handle,value,retry=1,response=False,type='public'):
		logging.debug('CONNECTOR------Writing Characteristic... ' + str(self.mac))
		iwriteCharacteristic=0
		while True:
			iwriteCharacteristic = iwriteCharacteristic + 1
			try:
				arrayValue = [int('0x'+value[i:i+2],16) for i in range(0, len(value), 2)]
				result = self.conn.writeCharacteristic(int(handle,16),struct.pack('<%dB' % (len(arrayValue)), *arrayValue),response)
				break
			except Exception as e:
				logging.debug(str(e))
				if iwriteCharacteristic >= retry:
					self.disconnect(True)
					if self.mac in globals.KEEPED_CONNECTION:
						del globals.KEEPED_CONNECTION[self.mac]
					return False
				logging.debug('CONNECTOR------Retry connection ' + str(self.mac))
				self.connect(type=type)
		logging.debug('CONNECTOR------Characteristic written... ' + str(self.mac))
		if result :
			logging.debug(str(result))
		return True

	def getCharacteristics(self,handle='',handleend='',retry=1,type='public'):
		logging.debug('CONNECTOR------Getting Characteristics... ' + str(self.mac))
		if handleend == '':
			handleend = handle
		igetCharacteristics=0
		while True:
			igetCharacteristics = igetCharacteristics + 1
			try:
				if handle == '':
					char = self.conn.getCharacteristics()
					break
				else:
					char = self.conn.getCharacteristics(int(handle,16), int(handleend,16)+4)
					break
			except Exception as e:
				logging.debug(str(e))
				if igetCharacteristics >= retry:
					self.disconnect(True)
					return False
				logging.debug('CONNECTOR------Retry connection ' + str(self.mac))
				self.connect(type=type)
		logging.debug('CONNECTOR------Characteristics gotten... '+ str(self.mac))
		return char

	def helper(self):
		logging.debug('CONNECTOR------Helper for : ' + str(self.mac))
		characteristics = self.getCharacteristics()
		listtype=['x','c','b','B','?','h','H','i','I','l','L','q','Q','f','d','s','p','P']
		for char in characteristics:
			handle = str(hex(char.getHandle()))
			if char.supportsRead():
				logging.debug('CONNECTOR------'+handle + ' readable')
			else:
				logging.debug('CONNECTOR------'+handle + ' not readable (probably only writable)')
			if char.supportsRead():
				try:
					value = char.read()
					found = False
					for type in listtype:
						for i in range(1,256):
							try:
								logging.debug('CONNECTOR------value for handle (decrypted with ' + type + ' lenght ' + str(i) +') : ' + handle + ' is : ' + str(struct.unpack(str(i)+type,value)))
								found = True
							except:
								continue
					logging.debug('CONNECTOR------value for handle (undecrypted) : ' + handle + ' is : ' + value)
				except Exception as e:
					logging.debug('CONNECTOR------unable to read value for handle (probably not readable) '+handle+ ' : '+str(e))
					continue
		return
