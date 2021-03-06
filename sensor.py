import numpy
#from obspy.core import Trace,Stream,UTCDateTime
import Queue
from threading import Thread
import os.path
import subprocess
import wiringpi as wp
import spidev
spi = spidev.SpiDev()

# GPIO Definition
CsPin    = 15
DrdyPin  = 11
ResetPin = 12

#switches
J1Pin = 32

# Register Addresses
REG_STATUS = 0x00
REG_MUX    = 0x01
REG_ADCON  = 0x02
REG_DRATE  = 0x03
REG_IO     = 0x04
REG_OFC0   = 0x05
REG_OFC1   = 0x06
REG_OFC2   = 0x07
REG_FSC0   = 0x08
REG_FSC1   = 0x09
REG_FSC2   = 0x0A

# sample rates
DRATE_30000 = 0b11110000
DRATE_15000 = 0b11100000
DRATE_7500  = 0b11010000
DRATE_3750  = 0b11000000
DRATE_2000  = 0b10110000
DRATE_1000  = 0b10100001
DRATE_500   = 0b10010010
DRATE_100   = 0b10000010
DRATE_60    = 0b01110010
DRATE_50    = 0b01100011
DRATE_30    = 0b01010011
DRATE_25    = 0b01000011
DRATE_15    = 0b00110011
DRATE_10    = 0b00100011
DRATE_5     = 0b00010011
DRATE_2_5   = 0b00000011

# Commands
CMD_WAKEUP   = 0x00
CMD_RDATA    = 0x01
CMD_RDATAC   = 0x03
CMD_SDATAC   = 0x0F
CMD_RREG     = 0x10
CMD_WREG     = 0x50
CMD_SELFCAL  = 0xF0
CMD_SELFOCAL = 0xF1
CMD_SELFGCAL = 0xF2
CMD_SYSOCAL  = 0xF3
CMD_SYSGCAL  = 0xF4
CMD_SYNC     = 0xFC
CMD_STANDBY  = 0xFD
CMD_RESET    = 0xFE

# Gain
DGAIN_1   = 0x00
DGAIN_2   = 0x01
DGAIN_4   = 0x02
DGAIN_8   = 0x03
DGAIN_16  = 0x04
DGAIN_32  = 0x05
DGAIN_65  = 0x06
DGAIN_128 = 0x07
 
def StartSPI(): 
    spi.open(0, 0) 
    spi.max_speed_hz = 1920000
    spi.mode = 0b01
    spi.lsbfirst = True

def StartGPIO():
    wp.wiringPiSetupPhys()
    wp.pinMode(CsPin, wp.OUTPUT)
    wp.pinMode(DrdyPin, wp.INPUT)
    wp.pinMode(ResetPin, wp.OUTPUT)
    wp.digitalWrite(CsPin, wp.HIGH)
    wp.digitalWrite(ResetPin, wp.HIGH)

def WaitDrdy():
    i = 0
    for i in range (400000):
        if(wp.digitalRead(DrdyPin) == 0):
            break
    if(i>=399999):
        print("DRDY time out")

def SendByte(data):
    wp.delayMicroseconds(2)
    spi.xfer([data])

def ReceiveByte():
    read = 0
    read = spi.xfer([0xff])
    return read[0]

def ChipSelect():
    wp.digitalWrite(CsPin, wp.LOW)

def ChipRelease():
    wp.digitalWrite(CsPin, wp.HIGH)

def DelayData():
    wp.delayMicroseconds(10)

def ReadReg(regID):
    read = 0    
    ChipSelect()
    SendByte(CMD_RREG|regID)
    SendByte(0x00)
    DelayData()
    read = ReceiveByte()
    return read

def WriteReg(regID, regValue):
    ChipSelect()
    SendByte(CMD_WREG|regID)
    SendByte(0x00)
    SendByte(regValue)
    ChipRelease()

def WriteCmd(cmd):
    ChipSelect()
    SendByte(cmd)
    ChipRelease()

def ReadChipID():
    ID = 0
    WaitDrdy()
    ID = ReadReg(REG_STATUS)
    return(ID>>4)

def SetChannal(ch):
    if(ch > 7):
        return
    WriteReg(REG_MUX, (ch << 4)|(1 << 3))

def SetDiffChannal(ch):
    if (ch == 0):
        WriteReg(REG_MUX, (0 << 4)|1)
    elif (ch == 1):
        WriteReg(REG_MUX, (2 << 4)|3)
    elif (ch == 2):
        WriteReg(REG_MUX, (4 << 4)|5)
    elif (ch == 3):
        WriteReg(REG_MUX, (6 << 4)|7)

def ReadData():
    read = 0
    ChipSelect()
    SendByte(CMD_RDATA)
    DelayData()

    #Read the 24bit sample result
    buff = spi.xfer([0xFF, 0xFF, 0xFF])
    read  = (numpy.uint32(numpy.int32(buff[0] << 16))) & 0x00FF0000
    read |= (numpy.uint32(numpy.int32(buff[1] <<  8)))
    read |= buff[2]
    ChipRelease()
    
    # Extend a signed number
    if(read & 0x800000):
        read |= 0xFF000000

    return numpy.int32(read)

def ISR():
    SetChannal(1)
    #SetDiffChannal(0)
    wp.delayMicroseconds(5)

    WriteCmd(CMD_SYNC)
    wp.delayMicroseconds(5)

    WriteCmd(CMD_WAKEUP)
    wp.delayMicroseconds(25)
        
    AdcNow = ReadData()
    return AdcNow    

def Scan():
    if (wp.digitalRead(DrdyPin) == 0):
        ISR()
        return 1
    return 0

def CfgADC(gain, drate):
    WaitDrdy()
    
    buff = [0,0,0,0]
    buff[0] = (0<<3)|(1<<2)|(0<<1)
    buff[1] = 0x08
    buff[2] = (0<<5)|(0<<3)|(gain<<0)
    buff[3] = drate

    ChipSelect()
    SendByte(CMD_WREG|0)
    SendByte(0x03)
    spi.xfer(buff)
    ChipRelease()

    wp.delayMicroseconds(50)

StartGPIO()
print("GPIO setup complete")

StartSPI()
print("SPI setup complete")

myID = ReadChipID()
print("Chip ID : " + str(myID))

CfgADC(DGAIN_1, DRATE_5)

#switches
wp.pinMode(J1Pin, wp.OUTPUT)
wp.digitalWrite(J1Pin, wp.LOW)



x=0
while (x<=200):
    while (wp.digitalRead(DrdyPin)==1):
        c=1
    Adc = ISR()    
    #print((Adc * 100) / 167 / 1000000.0)
    print ((Adc*2.5)/16777216.0)
    x+=1
    print x
wp.digitalWrite(J1Pin, wp.HIGH)
