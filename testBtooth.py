from __future__ import print_function
import bluetooth
import time
import sys

MACaddr = str(sys.argv[1])
print('Connecting to ' + MACaddr)

print ('\nServices (SL4A should appear):')
def what_services():
        for services in bluetooth.find_service(address = MACaddr):
	    print(services["name"])
            if services["name"] != 'SL4A': continue
            print("\t Name:           %s" % (services["name"]))
            print("\t Description:    %s" % (services["description"]))
            print("\t Protocol:       %s" % (services["protocol"]))
            print("\t Provider:       %s" % (services["provider"]))
            print("\t Port:           %s" % (services["port"]))
            print("\t service-classes %s" % (services["service-classes"]))
            print("\t profiles        %s" % (services["profiles"]))
            print("\t Service id:  %s" % (services["service-id"]))
            print("")
            return services["port"]

port = what_services()

print('\nTesting')
try:
	sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
	sock.connect((MACaddr, port))
	time.sleep(0.5)
	sock.send('50,200,50,200,50\n')
	time.sleep(3)
	sock.send('50,200,50,200,50\n')
	time.sleep(3)
	sock.close()
	time.sleep(7)
	sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
	sock.connect((MACaddr, port))
	time.sleep(0.5)
	sock.send('50,200,50,200,50\n')
	sock.close() # this hangs the connection
	time.sleep(6)
	sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
	sock.connect((MACaddr, port))
	time.sleep(0.5)
	sock.send('50,200,50,200,50\n')
	time.sleep(1)
	sock.close()

except bluetooth.btcommon.BluetoothError as btErr:
        errCode = eval(btErr[0])[0]
	print('errcode ',errCode)



