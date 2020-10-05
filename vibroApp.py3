from __future__ import print_function
#import android
from androidhelper import Android
import time
import sys
import traceback

droid = Android()

def BtoothCycle():
	print('Cycling Btooth receiver')
	droid.toggleBluetoothState(False)
	time.sleep(1)
	droid.toggleBluetoothState(True,False)
	time.sleep(3)

BtoothCycle()
droid.wakeLockAcquirePartial

ID = None;
while True:
	if ID: droid.bluetoothStop(ID)
	print('Accepting')
	try:
		ID = droid.bluetoothAccept().result # server
		while True:
			# print('ReadReady @ ID = %s' % (ID))
			k=0
			while not droid.bluetoothReadReady(ID).result and k<35: # wait loop
				sys.stdout.write('.'); sys.stdout.flush()
				time.sleep(0.2)
				k+=1
				if not droid.bluetoothActiveConnections().result: 
					k = 1000
					break
			if not k<35:
				if k<1000: print('More than 7 s idle.')
				else: 
					print('Connection lost') 
					BtoothCycle()
				break

			# print('ReadLine')
			try:
				s=droid.bluetoothReadLine(ID).result
			except: break
			if not s or len(s) < 9: continue
			a=eval('('+s+')') # dangerous code
#			print(s,a)
			print(a)
			if len(a) == 5:
				droid.vibrate(a[0]); time.sleep(float(a[0]+a[1])/1000)
				droid.vibrate(a[2]); time.sleep(float(a[2]+a[3])/1000)
				droid.vibrate(a[4]); time.sleep(float(a[4])/1000)
				droid.bluetoothWrite(s,ID) # Acknowledge. No newline needed on the way back
			else:
				# pass
				droid.bluetoothWrite(s+'@',ID) # Acknowledge improperly in case it is a format error. COM errors will be detected anyhow.
	except Exception as ex: # reconnect
		print(str(ex))
		traceback.print_exc()


