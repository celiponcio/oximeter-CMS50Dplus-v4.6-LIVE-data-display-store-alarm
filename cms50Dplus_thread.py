from __future__ import print_function

import csv
import datetime
import serial
import threading
import time
from copy import deepcopy


class _new_beat():
    def __init__(self):
        self.interval, \
        self.finger_out, \
        self.searching, \
        self.heartbeat, \
        self.strange_bits, \
        self.lagging = [None] * 6
        self.ok = False
        self.pulse_waveform = []
        self.pulse2_waveform = []
        self.PR = 45  # below 45 gives an alarm
        self.SpO2 = 100
        self.pulse_max, \
        self.pulse_avg, \
        self.pulse_min, \
        self.pulse2_max, \
        self.pulse2_avg, \
        self.pulse2_min = [0] * 6

class CMS(object):
    last_beat_time = False
    Nbeats = 0
    _stop_thread = False  # for gracefully stopping thread
    verbose = 0
    _start_time = time.time()
    _alive = True  # for checking if it is stuck somehwere in serial readout (it happens)

    def _print(self, *args, **kwargs):
        print("        CMS - %d - " % (time.time() - self._start_time) + " ".join(map(str, args)), **kwargs)

    def __init__(self, device, outfile):
        self.device = device
        self.outfile = outfile
        self.ser = serial.Serial()
        self.beat = _new_beat()
        self.oldbeat = _new_beat()

    def __del__(self):
        # self._print('deleting')
        self.stop()
        # self._print('properly deleted')

    def stop(self):
        self._stop_thread = True
        try:
            self._watchdog_timer.cancel()
        except:
            pass
        # while self.running(): time.sleep(0.01)
        self.thread.join()  # wait for thread to stop
        self.ser.close()
        # self._print('properly closed')

    def start(self):
        # handle errors, etc later
        self._start_time = time.time()
        self.thread = threading.Thread(target=self.aquire)
        self.thread.start()
        self._newTimer()

    def running(self):
        try:
            # return self.thread.is_alive() \
            #        and not self.error \
            #        and (self.beat.ok or self.beat.finger_out==None) # None means first data of a beat
            return self.thread.is_alive() and self.beat.ok
        except:
            return False

    def aquire(self):  # to run without sub-threading
        while True:
            self.error = False
            self._main_loop()
            self.error = True  # if it exited, some error occured
            self.ser.close()
            if not self._stop_thread:
                time.sleep(3)  # retry in case of error
            else:
                break  # to stop the thread

    def _newTimer(self):
        if self._stop_thread: return
        self._watchdog_timer = threading.Timer(5, self._watchdog)
        self._watchdog_timer.start()

    def _watchdog(self):
        if self.verbose >= 3: self._print('watchdog alive: ', self._print(self._alive))
        if self._stop_thread: return
        if not self._alive:  # no updates: stuck
            self.beat.ok = False  # main will see this through .running()
            # could try to reset the thread here (not native of threading mogule, but there are solutions online)
        else:
            self._alive = False
        self._newTimer()

    def _main_loop(self):

        self.beat = _new_beat()
        # self.oldbeat = _new_beat()
        self._alive = True

        if self.verbose >= 1:
            # sys.stdout.write("Connecting to device...\n"); sys.stdout.flush()
            self._print("Connecting to device...")

        try:
            self.ser.close()
        except:
            pass
        self._configure_serial()
        try:
            self.ser.open()
        except Exception as ex:
            self._print(ex)
            return

        if self.verbose >= 1:
            # sys.stdout.write("reading...\n"); sys.stdout.flush()
            self._print("reading...")

        try:
            self.ser.write(b'\x7d\x81\xa1\x80\x80\x80\x80\x80\x80')
        except Exception as ex:
            self._print(ex)
            return
        while not self._stop_thread:  # inner readout loop
            self._alive = True
            try:
                # self._print( self.ser.in_waiting) # check if the readout lags
                raw = self.ser.read(9)
                self.ser.read(
                    9)  # the heartbeat marker appears in 2 consecutive frames, so skip one. We don't need so much data.
                self.beat.lagging = self.ser.in_waiting
            except Exception as ex:
                self._print(ex)
                return
            if len(raw) <= 1:
                if self.verbose >= 1:
                    self._print("no data received. Is the device on?")
                return
            if self._process_raw(raw):
                if self.verbose >= 1:
                    self._print("some nonsense\n")
                return

    def _process_raw(self, raw):

        if len(raw) < 9: return True
        self.error = False

        now = datetime.datetime.now()
        if self.verbose >= 3:
            self._print(str(now), bin(ord(raw[1])), bin(ord(raw[2])), ord(raw[3]) & 0x7f, ord(raw[4]) & 0x7f,
                        ord(raw[5]) & 0x7f, ord(raw[6]) & 0x7f, ord(raw[7]) & 0x7f, ord(raw[8]) & 0x7f)  # debug line

        finger_out = bool(ord(raw[1]) & 0x1)
        if finger_out and not self.beat.finger_out:
            if self.verbose >= 1: self._print("finger out")
        self.beat.finger_out = finger_out

        searching = bool(ord(raw[1]) & 0x2)
        if searching and not self.beat.searching:
            if self.verbose >= 1: self._print("searching")
        self.beat.searching = searching

        ok = not (bool(ord(raw[1]) & 0x3))
        if ok and not self.beat.ok:
            if self.verbose >= 1: self._print("reading...")
        self.beat.ok = ok

        nonsense = (ord(raw[1]) & (0xff - 0x3)) ^ 0xe0  # these bits should be fixed
        self.beat.heartbeat = bool(ord(raw[2]) & 0x40)
        self.beat.strange_bits = ord(raw[2]) & 0x3
        nonsense += (ord(raw[2]) & (0xff - 0x47)) ^ 0x80  # these bits should be fixed
        self.beat.pulse_waveform.append(ord(raw[3]) & 0x7f)
        self.beat.pulse2_waveform.append(ord(raw[4]) & 0x7f)  # not sure about this
        self.beat.PR = ord(raw[5]) & 0x7f
        self.beat.SpO2 = ord(raw[6]) & 0x7f
        nonsense += ord(raw[7]) ^ 0xff  # these bits should be fixed
        nonsense += ord(raw[8]) ^ 0xff  # these bits should be fixed
        nonsense = bool(nonsense)

        nonsense = nonsense | \
                   self.beat.PR < 40 | self.beat.PR > 140 | \
                   self.beat.SpO2 > 99 | self.beat.SpO2 < 70
        if bool(nonsense):  # something wrong
            self._print(self.beat)
            return True

        if not self.beat.ok:
            self.last_beat_time = False

        if self.beat.heartbeat:
            self.ser.reset_input_buffer()  # don't allow readout lag to grow indefinitely
            if not self.last_beat_time:
                self.last_beat_time = now
            self.beat.interval = (now - self.last_beat_time).total_seconds()
            self._process_beat()
            self.last_beat_time = now
            self.oldbeat = deepcopy(self.beat)
            self.beat = _new_beat()
            self.beat.ok = self.oldbeat.ok  # transit state

        return False

    def _process_beat(self):
        self.Nbeats += 1
        p = self.beat.pulse_waveform
        self.beat.pulse_max = max(p)
        self.beat.pulse_min = min(p)
        self.beat.pulse_avg = round(float(sum(p)) / len(p), 1)
        p = self.beat.pulse2_waveform
        self.beat.pulse2_max = max(p)
        self.beat.pulse2_min = min(p)
        self.beat.pulse2_avg = round(float(sum(p)) / len(p), 1)
        if self.verbose >= 2:
            self._print("%.3f" % (self.beat.interval), '\t', self.beat.SpO2, self.beat.PR, \
                        '\t(', self.beat.pulse_max, self.beat.pulse_avg, self.beat.pulse_min, ')', \
                        '\t(', self.beat.pulse2_max, self.beat.pulse2_avg, self.beat.pulse2_min, ') ')
        self._write_beat()

    def _configure_serial(self):
        self.ser.baudrate = 115200  # 115200
        self.ser.bytesize = serial.EIGHTBITS  # 8
        self.ser.parity = serial.PARITY_NONE  # NONE
        self.ser.stopbits = serial.STOPBITS_ONE  # 1
        self.ser.xonxoff = 1  # XON/XOFF flow control
        self.ser.timeout = 0.5
        self.ser.port = self.device

    def _write_beat(self):
#        if not self.outfile or self.beat.interval == 0 or self.beat.interval > 1.9: return
        if not self.outfile: return
        fieldnames = ['interval', 'SpO2', 'PR',
                      'pulse_max', 'pulse_avg', 'pulse_min',
                      'pulse2_max', 'pulse2_avg', 'pulse2_min']
        to_write = {fieldname: getattr(self.beat, fieldname) for fieldname in fieldnames}
        with open(self.outfile, mode='a') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            #        writer.writeheader() # not with append
            writer.writerow(to_write)
