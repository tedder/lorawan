#!/usr/bin/env python3
import sys
from time import sleep
from SX127x.LoRa import *
from SX127x.LoRaArgumentParser import LoRaArgumentParser
from SX127x.board_config_ada import BOARD
import LoRaWAN
from LoRaWAN.MHDR import MHDR
from random import randrange
import reset_ada
BOARD.setup()
parser = LoRaArgumentParser("LoRaWAN sender")
UPFREQ = 903.9
DOWNFREQ = 923.3
class LoRaWANotaa(LoRa):
    def __init__(self, verbose = False):
        super(LoRaWANotaa, self).__init__(verbose)

    def on_rx_done(self):
        print("RxDone")

        self.clear_irq_flags(RxDone=1)
        payload = self.read_payload(nocheck=True)
        print(payload)
        self.set_mode(MODE.SLEEP)
        self.get_all_registers()
        print(self)
        lorawan = LoRaWAN.new([], appkey)
        lorawan.read(payload)
        print(lorawan.get_payload())
        print(lorawan.get_mhdr().get_mversion())

        if lorawan.get_mhdr().get_mtype() == MHDR.JOIN_ACCEPT:
            print("Got LoRaWAN join accept")
            print(lorawan.valid_mic())
            print(lorawan.get_devaddr())
            print(lorawan.derive_nwskey(devnonce))
            print(lorawan.derive_appskey(devnonce))
            print("\n")
            sys.exit(0)

        print("Got LoRaWAN message continue listen for join accept")

    def on_tx_done(self):
        self.clear_irq_flags(TxDone=1)
        print("TxDone")


        self.set_mode(MODE.SLEEP)
        self.set_dio_mapping([0,0,0,0,0,0])
        self.set_invert_iq(1)
        self.reset_ptr_rx()
        self.set_freq(DOWNFREQ)#915)        
        self.set_spreading_factor(7)#12)
        self.set_bw(9) #500Khz
        self.set_rx_crc(False)#TRUE
        self.set_mode(MODE.RXCONT)
        

    def start(self):
        self.tx_counter = 1

        lorawan = LoRaWAN.new(appkey)
        lorawan.create(MHDR.JOIN_REQUEST, {'deveui': deveui, 'appeui': appeui, 'devnonce': devnonce})

        self.write_payload(lorawan.to_raw())
        self.set_mode(MODE.TX)
        sleep(10)
        # lorawan.create(MHDR.UNCONF_DATA_UP, {'devaddr': devaddress, 'fcnt': 1, 'data': [0x12, 0x34] })

        # self.write_payload(lorawan.to_raw())
        # self.set_mode(MODE.TX)            



# Init
nwskey = [0xC3, 0x24, 0x64, 0x98, 0xDE, 0x56, 0x5D, 0x8C, 0x55, 0x88, 0x7C, 0x05, 0x86, 0xF9, 0x82, 0x26]
#A1C90EE49114C4AE
#7B6E502D545D0F90
#EEBC93D32166CE6FCEF7468CA6626649
devaddress = [0xDE, 0x00, 0x00, 0x48]
deveui = [0xA1, 0xC9, 0x0E, 0xE4, 0x91, 0x14, 0xC4, 0xAE]
appeui = [0x7B, 0x6E, 0x50, 0x2D, 0x54, 0x5D, 0x0F, 0x90]
appkey = [0xEE, 0xBC, 0x93, 0xD3, 0x21, 0x66, 0xCE, 0x6F, 0xCE, 0xF7, 0x46, 0x8C, 0xA6, 0x62, 0x66, 0x49] 
devnonce = [randrange(256), randrange(256)]
lora = LoRaWANotaa(True)

# Setup
lora.set_mode(MODE.SLEEP)
lora.set_dio_mapping([1,0,0,0,0,0])
lora.set_freq(UPFREQ)#915)
lora.set_pa_config(pa_select=1)
lora.set_spreading_factor(7)
lora.set_pa_config(max_power=0x0F, output_power=0x0E)
lora.set_sync_word(0x34)
lora.set_rx_crc(True)#TRUE
lora.get_all_registers()
print(lora)
assert(lora.get_agc_auto_on() == 1)

try:
    print("Sending LoRaWAN join request\n")
    lora.start()
    lora.set_mode(MODE.SLEEP)
    print(lora)
except KeyboardInterrupt:
    sys.stdout.flush()
    print("\nKeyboardInterrupt")
finally:
    sys.stdout.flush()
    lora.set_mode(MODE.SLEEP)
    BOARD.teardown()
