
 
'''
             define from bcm2835.h                       define from Board 
DVK511
                 3.3V | | 5V               ->                 3.3V | | 5V
    RPI_V2_GPIO_P1_03 | | 5V               ->                  SDA | | 5V 
    RPI_V2_GPIO_P1_05 | | GND              ->                  SCL | | GND
       RPI_GPIO_P1_07 | | RPI_GPIO_P1_08   ->                  IO7 | | TX
                  GND | | RPI_GPIO_P1_10   ->                  GND | | RX
       RPI_GPIO_P1_11 | | RPI_GPIO_P1_12   ->                  IO0 | | IO1
    RPI_V2_GPIO_P1_13 | | GND              ->                  IO2 | | GND
       RPI_GPIO_P1_15 | | RPI_GPIO_P1_16   ->                  IO3 | | IO4
                  VCC | | RPI_GPIO_P1_18   ->                  VCC | | IO5
       RPI_GPIO_P1_19 | | GND              ->                 MOSI | | GND
       RPI_GPIO_P1_21 | | RPI_GPIO_P1_22   ->                 MISO | | IO6
       RPI_GPIO_P1_23 | | RPI_GPIO_P1_24   ->                  SCK | | CE0
                  GND | | RPI_GPIO_P1_26   ->                  GND | | CE1

::if your raspberry Pi is version 1 or rev 1 or rev A
RPI_V2_GPIO_P1_03->RPI_GPIO_P1_03
RPI_V2_GPIO_P1_05->RPI_GPIO_P1_05
RPI_V2_GPIO_P1_13->RPI_GPIO_P1_13
::
'''

import numpy
import Queue
from threading import Thread
import os.path
import subprocess
import wiringpi as wp
import spidev
import time

#//CS      -----   SPICS  
#//DIN     -----   MOSI
#//DOUT  -----   MISO
#//SCLK   -----   SCLK
#//DRDY  -----   ctl_IO     data  starting
#//RST     -----   ctl_IO     reset

spi = spidev.SpiDev()
spi.open(0, 0) 
spi.max_speed_hz = 1920000
spi.mode = 0b01
spi.lsbfirst = True

#define	SPICS	RPI_GPIO_P1_16	//P4
SPICS    = 16
RES1PIN = 29
RES2PIN = 31

wp.wiringPiSetupPhys()
wp.pinMode(SPICS, wp.OUTPUT)
wp.pinMode(RES1PIN, wp.OUTPUT)
wp.pinMode(RES2PIN, wp.OUTPUT)

def CS_1():
    wp.digitalWrite(SPICS, wp.HIGH)

def CS_0():
	wp.digitalWrite(SPICS, wp.LOW)

channel_A =  0x30
channel_B =  0x34

def DelayUS(micros):
    wp.delayMicroseconds(micros)

def Write_DAC8532(channel, _Data):
    buff = [0,0,0]
    CS_1() 
    CS_0() 
    buff = [channel,(_Data>>8),(_Data&0xff)]
    spi.xfer(buff)
    CS_1() 

def Voltage_Convert(Vref, voltage):
	return int(65536 * voltage / Vref)
    

def test_dac8553():

  i = 0.0
  tmp=0

  while 1:
    if (tmp==0):
        Write_DAC8532(0x30, Voltage_Convert(5.0,0.00+i/10))     #Write channel A buffer (0x30)
        Write_DAC8532(0x34, Voltage_Convert(5.0,5.000-i/10))    #Write channel B buffer (0x34)   
        i+=1

        if (i==50):
            i=0
            tmp=1
        DelayUS(50000)
      
    elif (tmp==1):
        Write_DAC8532(0x30, Voltage_Convert(5.0,5.000-i/10))   #Write channel B buffer (0x30) 
        Write_DAC8532(0x34, Voltage_Convert(5.0,0.00+i/10))   #Write channel A buffer (0x34)  
        i+=1

        if(i==50):
            i=0
            tmp=0

        DelayUS(50000)
        
def test_voltage(_voltage,_duration):
    start_time = time.time()
    now = time.time()
    data = Voltage_Convert(3.000,_voltage)
    while (now-start_time<=_duration):
        Write_DAC8532(0x30,data)
        now = time.time()
        print now-start_time
    Write_DAC8532(0x30,0)


wp.digitalWrite(RES1PIN, wp.LOW)
wp.digitalWrite(RES2PIN, wp.LOW)
#test_dac8553()
test_voltage(2.024,600) 

