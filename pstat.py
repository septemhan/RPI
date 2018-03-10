import numpy
#from obspy.core import Trace,Stream,UTCDateTime
import Queue
from threading import Thread
import time
import wiringpi as wp
import spidev
import math
spi = spidev.SpiDev()

# GPIO Definition
CsPin    = 15
DrdyPin  = 11
ResetPin = 12
SPICS    = 16


#switches
J1Pin = 32
RES11PIN = 29
RES21PIN = 31
RES12PIN = 33
RES22PIN = 35


#DAC address
channel_A =  0x30
channel_B =  0x34

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

    wp.pinMode(SPICS, wp.OUTPUT)
    wp.pinMode(RES11PIN, wp.OUTPUT)
    wp.pinMode(RES12PIN, wp.OUTPUT)
    wp.pinMode(RES21PIN, wp.OUTPUT)
    wp.pinMode(RES22PIN, wp.OUTPUT)

def CS_1():
    wp.digitalWrite(SPICS, wp.HIGH)

def CS_0():
    wp.digitalWrite(SPICS, wp.LOW)

def Write_DAC8532(channel, _Data):
    buff = [0,0,0]
    CS_1() 
    CS_0() 
    buff = [channel,(_Data>>8),(_Data&0xff)]
    spi.xfer(buff)
    CS_1() 

def Voltage_Convert(Vref, voltage):
    return int(65536 * voltage / Vref)

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

def ISR(_ch):
    SetChannal(_ch)
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

CfgADC(DGAIN_1, DRATE_10)

def EC_test():

    #switches
    wp.pinMode(J1Pin, wp.OUTPUT)
    wp.digitalWrite(J1Pin, wp.LOW)



    x=0
    while (x<=200):
        while (wp.digitalRead(DrdyPin)==1):
            c=1
        Adc = ISR(1)   #ch1 is for EC module 
        #print((Adc * 100) / 167 / 1000000.0)
        print ((Adc*2.5)/16777216.0)
        x+=1
        print x
    wp.digitalWrite(J1Pin, wp.HIGH)


def ISE_test(_ch):
    x=0
    while (x<=5000):
        while (wp.digitalRead(DrdyPin)==1):
            c=1
        Adc = ISR(_ch)   #ch1 is for EC module 
        #print((Adc * 100 ) / 167 / 1000000.0)
        print ((Adc*12.000)/16777216.0)
        x+=1

def test_voltage(_voltage,_duration):
    start_time = time.time()
    now = time.time()
    data = Voltage_Convert(3.000,_voltage)
    while (now-start_time<=_duration):
        Write_DAC8532(0x30,data)
        now = time.time()
        print now-start_time
    Write_DAC8532(0x30,0)

def test_pstas_1(_voltage,_duration,_resolution):
    print "setting resultion"
    if (_resolution==1): #100k
        wp.digitalWrite(RES11PIN, wp.LOW)
        wp.digitalWrite(RES21PIN, wp.LOW)
        print "res =1X"
    elif (_resolution==2):#1M
        wp.digitalWrite(RES11PIN, wp.HIGH)
        wp.digitalWrite(RES21PIN, wp.LOW)
        print "res =10X"
    elif (_resolution==3):#10M
        wp.digitalWrite(RES11PIN, wp.LOW)
        wp.digitalWrite(RES21PIN, wp.HIGH)
        print "res =100X"
    elif (_resolution==4):#100M
        wp.digitalWrite(RES11PIN, wp.HIGH)
        wp.digitalWrite(RES21PIN, wp.HIGH)
        print "res =1000X"

    print "resolution setting completed"

    
    start_time = time.time()
    now = time.time()
    data = Voltage_Convert(3.000,_voltage)
    while (now-start_time<=_duration):
        Write_DAC8532(0x30,data)
        while (wp.digitalRead(DrdyPin)==1):pass
        Adc = ISR(7)   #ch7 is for PS1 ch0 is forPS2 
        #I = ((Adc * 100) / 167 / 1000000.0)
        I =  ((Adc*12.0)/16777216.0)
        result.append(I)
        now = time.time()
        print int(now-start_time),I, '\n'
    #Write_DAC8532(0x30,0)

result = []
def test_pstas_2(_voltage,_duration,_resolution):
    print "setting resultion"
    if (_resolution==1): #100
        wp.digitalWrite(RES12PIN, wp.LOW)
        wp.digitalWrite(RES22PIN, wp.LOW)
        F = 100
        print "res =1X"
    elif (_resolution==2):#1k
        wp.digitalWrite(RES12PIN, wp.HIGH)
        wp.digitalWrite(RES22PIN, wp.LOW)
        F = 1000
        print "res =10X"
    elif (_resolution==3):#10k
        wp.digitalWrite(RES12PIN, wp.LOW)
        wp.digitalWrite(RES22PIN, wp.HIGH)
        F = 10000
        print "res =100X"
    elif (_resolution==4):#100k unit micr0-amps
        wp.digitalWrite(RES12PIN, wp.HIGH)
        wp.digitalWrite(RES22PIN, wp.HIGH)
        F = 100000.0/1000000.0
        print "res =1000X"

    print "resolution setting completed"

    
    start_time = time.time()
    now = time.time()
    data = Voltage_Convert(3.000,_voltage)
    while (now-start_time<=_duration):
        Write_DAC8532(0x34,data)
        while (wp.digitalRead(DrdyPin)==1):pass
        Adc = ISR(0)   #ch7 is for PS1 ch0 is forPS2 
        #I = ((Adc * 100) / 167 / 1000000.0)
        I =  ((Adc*12.000)/16777216.0)/F
        result.append(I)
        now = time.time()
        #print int(now-start_time),I, '\n'
    #Write_DAC8532(0x30,0)

#wp.digitalWrite(RES1PIN, wp.LOW)
#wp.digitalWrite(RES2PIN, wp.HIGH)
#wirte_V = -0.5000000
#test_pstas_2(wirte_V+1.024,10,4)
#test_pstas_2(wirte_V+1.024,20,2)
#test_voltage(1.024,120)
ISE_test(4)

def var(l):
    s1=0
    s2=0
    for i in l:
        s1+=i**2
        s2+=i
    return float(s1)/len(l)-(float(s2)/len(l))**2
def clean(l,ave):
    for i in l:
        if abs(i-ave)/i>=0.15:
            l.remove(i)
'''
wirte_V = 0.5000000
filename = "Low_NOISE_test_1"
tempfile = open(filename,'w')
CfgADC(DGAIN_1, DRATE_30000)
#for drate in [DRATE_10,DRATE_100,DRATE_500,DRATE_1000,DRATE_7500,DRATE_30000]:
for v in [0,0.1,0.2,0.5,0.7,0.9]:
    #CfgADC(DGAIN_1, drate)
    wirte_V = v    
    for i in range(10):            
        result = []

        test_pstas_2(wirte_V+1.024,10,1)
        a = sum(result)/len(result)
        #result = clean(result,ave)

        ave = sum(result)/len(result)
        std = math.sqrt(var(result))
        rsd = std/ave

        lineTowirte = str(i)+","+str(ave)+","+str(std)+","+str(rsd)+"\n"
        tempfile.write(lineTowirte)

tempfile.close()
'''
