from __future__ import print_function
import bluetooth
import sys, time, threading
from subprocess import call

def _print(*args, **kwargs):
    print("    VIB - "+" ".join(map(str,args)), **kwargs)


class Vibrate(object):
    MACaddr = None
    verbose = 0
    connection_trials = 0
    _sock = None
    _busy = False
    _stopping = False
    main_is_alive = True
    veto = True

    class signal():
        PR = "500,200,50,0,0"  # too low pulse rate
        disconnected = '50,200,50,0,0'
        main_dead = '50,200,50,200,50'  # is issued by vibroApp if it fails to be updated = main is dead

    def __init__(self, MACaddr):
        self.MACaddr = MACaddr
        if not self._connect(): # try to connect
            self.connection_trials += 1 # signal not connected
        self._newTimer()  # watchdog will carry on

    # def __del__(self):
    #     self.stop()

    def stop(self):
        if self.verbose > 0: _print("deleting Vibrate instance")
        self._stopping = True
        self._watchdog_timer.cancel()
        try: self._sock.close()
        except: pass

    def running(self):
        # _print(self.connection_trials,self._sock)
        return not self.connection_trials and self._sock

    def _newTimer(self):
        if self._stopping: return
        self._watchdog_timer = threading.Timer(6, self._watchdog)
        self._watchdog_timer.start()

    def _watchdog(self):
        if self._busy:
            self._newTimer()
            return
        if self.main_is_alive:
            s = self.vibrate('0,0,0,0,0') # report all ok
        else:
            s = self.vibrate(self.signal.main_dead)
        self.main_is_alive = False # main has 6 seconds to set this
        if s:
            self.connection_trials = 0
            self._newTimer()
            return # connection ok
        # no connection
        if self.verbose > 0: _print("reconnecting to %s " % (self.MACaddr))
        self.connection_trials += 1 # signal not connected
        time.sleep(8) # this resets vibroApp to start listening for connection
        if self._stopping: return
        if self._connect():
            self.connection_trials = 0
        self._newTimer()

    def _connect(self):
        if self.verbose > 0: _print("connecting to %s " % (self.MACaddr))
        port = self._what_services()
        if not port and self.verbose > 0:
            _print('No SL4A service in %s' % (self.MACaddr))
            _print('is the MAC address correct?')
            _print('is the Vibro app running?')
            return False
        if self.verbose > 0: _print("connecting to %s" % (self.MACaddr))
        # Create the client socket
        try:
            try: self._sock.close()
            except: pass
            self._sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
            self._sock.connect((self.MACaddr, port))
        except Exception as ex:
            if self.verbose > 0: _print(str(ex), "connection error.")
            try: self._sock.close()
            except: pass
            self._sock=None
            return False
        if self.verbose > 0: _print("connected.")
        return True

    def _what_services(self):
        for services in bluetooth.find_service(address = self.MACaddr):
            if services["name"] != 'SL4A': continue
            if self.verbose > 1:
                _print("\t Name:           %s" % (services["name"]))
                _print("\t Description:    %s" % (services["description"]))
                _print("\t Protocol:       %s" % (services["protocol"]))
                _print("\t Provider:       %s" % (services["provider"]))
                _print("\t Port:           %s" % (services["port"]))
                _print("\t service-classes %s" % (services["service-classes"]))
                _print("\t profiles        %s" % (services["profiles"]))
                _print("\t Service id:  %s" % (services["service-id"]))
                _print("")
            return services["port"]

    def vibrate(self,s):
        if self.connection_trials or not self._sock: # not connected
            return False
        if not s=='0,0,0,0,0' and self.veto:
            return True
        while self._busy:
            time.sleep(0.1)
        self._busy = True
        try:
            self._sock.send(s + '\n')
            data = self._sock.recv(1024) # receive identical reply
            if len(data) == 0:
                self._busy = False
                return False
            if self.verbose > 1: _print("received %s" % data,s==data)
            self._busy = False
            return s==data
            #_print([ord(a) for a in s])
            #_print([ord(a) for a in data])
        except:
            self._busy = False
            return False



