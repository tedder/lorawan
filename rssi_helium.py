#!/usr/bin/env python3
import sys
import argparse
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

import RPi.GPIO as GPIO

import helium

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
UPFREQ = 903.9
DOWNFREQ = 923.3


# Create the I2C interface.
i2c = busio.I2C(board.SCL, board.SDA)

# 128x32 OLED Display
reset_pin = DigitalInOut(board.D4)
display = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c, reset=reset_pin)
# Clear the display.
display.fill(0)
display.text('LoRA!', 0, 0, 1)
display.show()
width = display.width
height = display.height

global msg
msg = 'Test'

class LoRaWANotaa(LoRa):
    def __init__(self, verbose = False):
        super(LoRaWANotaa, self).__init__(verbose)

    def on_rx_done(self):
        print("RxDone")

        self.clear_irq_flags(RxDone=1)
        payload = self.read_payload(nocheck=True)
        print(payload)

        lorawan = LoRaWAN.new(helium.nwskey, helium.appskey)
        lorawan.read(payload)
        print(lorawan.get_mhdr().get_mversion())
        print(lorawan.get_mhdr().get_mtype())
        print(lorawan.get_mic())
        print(lorawan.compute_mic())
        print(lorawan.valid_mic())
        print("".join(list(map(chr, lorawan.get_payload()))))
        print("\n")

        self.set_mode(MODE.STDBY)

        s = ''
        s += " pkt_snr_value  %f\n" % self.get_pkt_snr_value()
        s += " pkt_rssi_value %d\n" % self.get_pkt_rssi_value()
        s += " rssi_value     %d\n" % self.get_rssi_value()
        display.fill(0)
        display.text(s, 0, 0, 1)
        display.show()
        print(s)


        
    def tx(self):
        global msg
        #self.tx_counter += 1
        lorawan = LoRaWAN.new(helium.nwskey, helium.appskey)
        lorawan.create(MHDR.CONF_DATA_UP, {'devaddr': helium.devaddr, 'fcnt': self.tx_counter, 'data': list(map(ord, msg)) })
        print("tx: {}".format(lorawan.to_raw()))
        self.write_payload(lorawan.to_raw())
        self.set_mode(MODE.TX)
        display.fill(0)
        display.text('Transmit!', 0, 0, 1)
        display.show()

    def start(self):
        self.setup_tx()
        self.tx()
        while True:
            sleep(.1)
            if not btnB.value:
                self.setup_tx()
                self.tx()                

    def set_frame(self,frame):
        self.tx_counter = frame

    def setup_tx(self):
    # Setup
        self.clear_irq_flags(RxDone=1)
        self.set_mode(MODE.SLEEP)
        self.set_dio_mapping([1,0,0,0,0,0])
        self.set_freq(UPFREQ)
        self.set_bw(7)
        self.set_spreading_factor(7)
        self.set_pa_config(max_power=0x0F, output_power=0x0E)
        self.set_sync_word(0x34)
        self.set_rx_crc(True)
        self.set_invert_iq(0)
        assert(self.get_agc_auto_on() == 1)        

    def on_tx_done(self):
        self.clear_irq_flags(TxDone=1)
        print("TxDone")
        self.set_mode(MODE.SLEEP)
        self.set_dio_mapping([0,0,0,0,0,0])
        self.set_freq(DOWNFREQ)         
        self.set_bw(9)
        self.set_spreading_factor(7)        
        self.set_pa_config(pa_select=1)
        self.set_sync_word(0x34)
        self.set_rx_crc(False)
        self.set_invert_iq(1)

        self.reset_ptr_rx()
        self.set_mode(MODE.RXCONT)

def init(frame):
    lora = LoRaWANotaa(True)
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
    global frame
    global msg
    # parser = argparse.ArgumentParser(add_help=True, description="Trasnmit a LoRa msg")
    # parser.add_argument("--frame", help="Message frame")
    # parser.add_argument("--msg", help="tokens file")
    # args = parser.parse_args()
    # frame = int(args.frame)
    # msg = args.msg
    frame = 118
    msg = 'Test'
    init(frame)

if __name__ == "__main__":
    main()