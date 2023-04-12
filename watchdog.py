#
# Wrapper for the standard micropython watchdog timer with
# added behavior to disable and re-enable the watchdog timer depending on what I am doing.
#
# Record the most recent feeder_index which must be a single byte
# in the pcf85063a scratch storage.
#
# This file is RP2040 specific.
#
from micropython import const
from machine import mem32, WDT

from pcf_badger import pcf_chip

class WATCHDOG :

    WDT_BASE = const(0x40058000)

    WDT_CTRL   = const(WDT_BASE + 0x00)
    WDT_REASON = const(WDT_BASE + 0x08)
    
    #
    # Bitmasks in CTRL register to enable/disable the watchdog time
    #
    
    WDT_CTRL_ENABLE_MASK = const(0b0100_0000_0000_0000_0000_0000_0000_0000)
    WDT_REASON_MASK      = const(0b0000_0000_0000_0000_0000_0000_0000_0001)

    def __init__(self, timeout_ms) :
        self.__wdt = WDT(timeout=timeout_ms)
        self.disable()
        self.__rtc_chip = pcf_chip()

    def feed(self, feeder_index) :
        self.__wdt.feed()
        self.__rtc_chip.set_byte(feeder_index)

    def enable(self) :
        # Feed the timer before enabling to ensure the app gets a full timeout.
        self.feed(0)
        mem32[WDT_CTRL] |= WDT_CTRL_ENABLE_MASK
                
    def disable(self) :
        mem32[WDT_CTRL] &= ~WDT_CTRL_ENABLE_MASK

    #
    # Specifically did the reboot happen because
    # the watchdog expired?
    # 
    def caused_reboot(self) :
        reason = mem32[WDT_REASON]
        return (reason & WDT_REASON_MASK) != 0

