#!/usr/bin/env python3

import json
import sys
import argparse
import datetime
from time import sleep
from SX127x.LoRa import *
from SX127x.LoRaArgumentParser import LoRaArgumentParser
from SX127x.board_config_ada import BOARD
import LoRaWAN
from LoRaWAN.MHDR import MHDR
from random import randrange
import reset_ada
# Import the SSD1306 module.
import adafruit_ssd1306
from digitalio import DigitalInOut, Direction, Pull
import board
import busio
import os
import re
import shortuuid

import RPi.GPIO as GPIO

import helium
import keys

# Button A
btnA = DigitalInOut(board.D5)
btnA.direction = Direction.INPUT
btnA.pull = Pull.UP

# Button B
btnB = DigitalInOut(board.D6)
btnB.direction = Direction.INPUT
btnB.pull = Pull.UP

# Button C
btnC = DigitalInOut(board.D12)
btnC.direction = Direction.INPUT
btnC.pull = Pull.UP

BOARD.setup()
parser = LoRaArgumentParser("LoRaWAN sender")


# Create the I2C interface.
i2c = busio.I2C(board.SCL, board.SDA)

# 128x32 OLED Display
reset_pin = DigitalInOut(board.D4)
display = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c, reset=reset_pin)
# Clear the display.
display.fill(0)
display.text("Test is ready to start!", 0, 0, 1)
display.text('Push Left Button', 0, 10, 1)
display.text('To start test.', 0, 20, 1)
display.show()
width = display.width
height = display.height

global test_status
test_status = {"running_ping": False, "ping_count": 0, "last_ping_time": None}

global last_test
last_test = None

class LoRaWANotaa(LoRa):
    def __init__(self, verbose = False, ack=True):
        super(LoRaWANotaa, self).__init__(verbose)
        self.iter = 0
        self.uuid = shortuuid.uuid()
        self.ack = ack

    def on_rx_done(self):
        global test_status
        self.clear_irq_flags(RxDone=1)
        payload = self.read_payload(nocheck=True)
        print(f"Raw payload: {payload}")

        lorawan = LoRaWAN.new(keys.nwskey, keys.appskey)
        lorawan.read(payload)
        decoded = "".join(list(map(chr, lorawan.get_payload())))
        print(f"Decoded: {decoded}\n")

        if " " in decoded:
            test_status["last_ping_time"] = decoded.split(" ")[1]
        test_status["ping_count"] += 1

        if lorawan.get_mhdr().get_mtype() == MHDR.UNCONF_DATA_DOWN:
            print("Unconfirmed data down.")
            downlink = decoded
            res = lorawan.mac_payload.get_fhdr().get_fctrl()
            if 0x20 & res != 0: # Check Ack bit.
                print("Server ack")
                if len(downlink) == 0:
                    downlink = "Server ack"
        elif lorawan.get_mhdr().get_mtype() == MHDR.CONF_DATA_DOWN:
            print("Confirmed data down.")
            self.ack = True
            downlink = decoded            
        elif lorawan.get_mhdr().get_mtype() == MHDR.CONF_DATA_UP:
            print("Confirmed data up.")
            downlink = decoded                        
        else:
            print("Other packet.")
            downlink = ''


        self.set_mode(MODE.STDBY)

        s = ''
        s += " pkt_snr_value  %f\n" % self.get_pkt_snr_value()
        s += " pkt_rssi_value %d\n" % self.get_pkt_rssi_value()
        s += " rssi_value     %d\n" % self.get_rssi_value()
        s += " msg: %s" % downlink
        #display.fill(0)
        #display.text(s, 0, 0, 1)
        #display.show()
        print(s)

    def increment(self):
        self.tx_counter += 1

        data_file = open("frame.txt", "w")
        data_file.write(f'frame = {self.tx_counter}\n')
        data_file.close()

    def tx(self, msg, conf=True):
        if conf:
            data = MHDR.CONF_DATA_UP
            print('Sending confirmed data up.')
        else:
            data = MHDR.UNCONF_DATA_UP
            print('Sending unconfirmed data up.')            
        self.increment()

        print(f"tx keys: {keys.nwskey}, {keys.appskey}, {keys.devaddr}")
        lorawan = LoRaWAN.new(keys.nwskey, keys.appskey)
        if self.ack:
            print('Sending with Ack')
            lorawan.create(data, {'devaddr': keys.devaddr, 'fcnt': self.tx_counter, 'data': list(map(ord, msg)), 'ack':True})
            self.ack = False
        else:
            print('Sending without Ack')
            print(data, {'devaddr': keys.devaddr, 'fcnt': self.tx_counter, 'data': list(map(ord, msg))})
            lorawan.create(data, {'devaddr': keys.devaddr, 'fcnt': self.tx_counter, 'data': list(map(ord, msg))})
        print(f"data: {list(map(ord, msg))}")
        print(f"tx: {lorawan.to_raw()}")
        self.write_payload(lorawan.to_raw())
        self.set_mode(MODE.TX)

        display.fill(0)
        display.text('Transmit!', 0, 0, 1)
        display.show()
        print("tx done")

    def start(self):
        msg = json.dumps({"i": self.iter, "s": self.uuid})
        self.setup_tx()
        self.tx(msg)
        while True:
            sleep(.1)
            display.fill(0)
            display.text(f'Test is {str(test_status["running_ping"])}', 0, 0, 1)
            display.text(f'Time: {str(test_status["last_ping_time"])}', 0, 10, 1)
            display.text(f'Total Pings: {test_status["ping_count"]}', 0, 20, 1)
            display.show()
            if test_status["running_ping"] and not last_test or (last_test and (datetime.datetime.now() - last_test).seconds > 5):
                self.setup_tx()
                self.tx(msg)
            if not btnC.value:
                self.setup_tx()
                self.tx(msg, False)                                   

    def set_frame(self,frame):
        self.tx_counter = frame

    def setup_tx(self):
    # Setup
        self.clear_irq_flags(RxDone=1)
        self.set_mode(MODE.SLEEP)
        self.set_dio_mapping([1,0,0,0,0,0])
        self.set_freq(helium.UPFREQ)
        self.set_bw(7)
        self.set_spreading_factor(7)
        self.set_pa_config(max_power=0x0F, output_power=0x0E)
        self.set_sync_word(0x34)
        self.set_rx_crc(True)
        self.set_invert_iq(0)
        assert(self.get_agc_auto_on() == 1)        

    def on_tx_done(self):
        print("on_tx_done")
        self.clear_irq_flags(TxDone=1)
        self.set_mode(MODE.SLEEP)
        self.set_dio_mapping([0,0,0,0,0,0])
        self.set_freq(helium.DOWNFREQ)         
        self.set_bw(9)
        self.set_spreading_factor(7)        
        self.set_pa_config(pa_select=1)
        self.set_sync_word(0x34)
        self.set_rx_crc(False)
        self.set_invert_iq(1)
        self.reset_ptr_rx()
        self.set_mode(MODE.RXCONT)

def init():
    lora = LoRaWANotaa(False)

    frame = 0
    if os.path.exists('frame.txt'):
        with open('frame.txt') as df:
            for line in df:
                if m := re.match('^frame\s*=\s*(\d+)', line):
                    frame = int(m.group(1))

    lora.set_frame(frame)

    try:
        print("Sending LoRaWAN tx\n")
        lora.start()
    except KeyboardInterrupt:
        sys.stdout.flush()
        print("\nKeyboardInterrupt")
    finally:
        sys.stdout.flush()
        lora.set_mode(MODE.SLEEP)
        BOARD.teardown()


def main():
    # parser = argparse.ArgumentParser(add_help=True, description="Trasnmit a LoRa msg")
    # parser.add_argument("--frame", help="Message frame")
    # parser.add_argument("--msg", help="tokens file")
    # args = parser.parse_args()
    # frame = int(args.frame)
    init()

if __name__ == "__main__":
    main()
