import numpy
#from obspy.core import Trace,Stream,UTCDateTime
import Queue
import threading
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

class DAC():
    def __init__(self):
        self.Vref = 3.0000
        self.PSref = 1.02400

    def Write_data(self,_Data,_ch):
        buff = [0,0,0]
        self.CS_1() 
        self.CS_0() 
        buff = [_ch,(_Data>>8),(_Data&0xff)]
        spi.xfer(buff)
        self.CS_1() 

    def Voltage_Convert(self, _voltage):
        return int(65536 * _voltage / self.Vref)


    def CS_1(self):
        wp.digitalWrite(SPICS, wp.HIGH)

    def CS_0(self):
        wp.digitalWrite(SPICS, wp.LOW)

    def write(self,_voltage,_ch):
        voltageTowrite = self.PSref+_voltage
        dataTowrite = self.Voltage_Convert(voltageTowrite)
        self.Write_data(dataTowrite,_ch)
    

class ADCMonitor(threading.Thread):
    def __init__(self,_data_q,_ch):
        self.data_q = _data_q
        self.ch = _ch
        threading.Thread.__init__(self)
        self.start_ts = time.time()
        self.sample_On = False

    def WaitDrdy(self):
        i = 0
        for i in range (400000):
            if(wp.digitalRead(DrdyPin) == 0):
                break
        if(i>=399999):
            print("DRDY time out")

    def SendByte(self,_data):
        wp.delayMicroseconds(2)
        spi.xfer([_data])

    def ReceiveByte(self):
        read = 0
        read = spi.xfer([0xff])
        return read[0]

    def ChipSelect(self):
        wp.digitalWrite(CsPin, wp.LOW)

    def ChipRelease(self):
        wp.digitalWrite(CsPin, wp.HIGH)

    def DelayData(self):
        wp.delayMicroseconds(10)

    def ReadReg(self,regID):
        read = 0    
        self.ChipSelect()
        self.SendByte(CMD_RREG|regID)
        self.SendByte(0x00)
        self.DelayData()
        read = self.ReceiveByte()
        return read

    def WriteReg(self,regID, regValue):
        self.ChipSelect()
        self.SendByte(CMD_WREG|regID)
        self.SendByte(0x00)
        self.SendByte(regValue)
        self.ChipRelease()

    def WriteCmd(self,_cmd):
        self.ChipSelect()
        self.SendByte(_cmd)
        self.ChipRelease()

    def ReadChipID(self):
        ID = 0
        self.WaitDrdy()
        ID = self.ReadReg(REG_STATUS)
        return(ID>>4)

    def SetChannal(self,_ch):
        if(_ch > 7):
            return
        self.WriteReg(REG_MUX, (_ch << 4)|(1 << 3))

    def SetDiffChannal(self,ch):
        if (ch == 0):
            self.WriteReg(REG_MUX, (0 << 4)|1)
        elif (ch == 1):
            self.WriteReg(REG_MUX, (2 << 4)|3)
        elif (ch == 2):
            self.WriteReg(REG_MUX, (4 << 4)|5)
        elif (ch == 3):
            self.WriteReg(REG_MUX, (6 << 4)|7)

    def ReadData(self):
        read = 0
        self.ChipSelect()
        self.SendByte(CMD_RDATA)
        self.DelayData()

        #Read the 24bit sample result
        buff = spi.xfer([0xFF, 0xFF, 0xFF])
        read  = (numpy.uint32(numpy.int32(buff[0] << 16))) & 0x00FF0000
        read |= (numpy.uint32(numpy.int32(buff[1] <<  8)))
        read |= buff[2]
        self.ChipRelease()
        
        # Extend a signed number
        if(read & 0x800000):
            read |= 0xFF000000

        return numpy.int32(read)

    def ISR(self):
        self.SetChannal(self.ch)
        #SetDiffChannal(0)
        wp.delayMicroseconds(5)

        self.WriteCmd(CMD_SYNC)
        wp.delayMicroseconds(5)

        self.WriteCmd(CMD_WAKEUP)
        wp.delayMicroseconds(25)
            
        AdcNow = self.ReadData()
        return AdcNow    

    def Scan(self):
        if (wp.digitalRead(DrdyPin) == 0):
            self.ISR()
            return 1
        return 0

    def CfgADC(self,gain, drate):
        self.WaitDrdy()
        
        buff = [0,0,0,0]
        buff[0] = (0<<3)|(1<<2)|(0<<1)
        buff[1] = 0x08
        buff[2] = (0<<5)|(0<<3)|(gain<<0)
        buff[3] = drate

        self.ChipSelect()
        self.SendByte(CMD_WREG|0)
        self.SendByte(0x03)
        spi.xfer(buff)
        self.ChipRelease()

        wp.delayMicroseconds(50)

    def run(self):

        myID = self.ReadChipID()
        print("Chip ID : " + str(myID))

        self.CfgADC(DGAIN_1, DRATE_10)
        self.sample_On = True

        while (self.sample_On):
            while (wp.digitalRead(DrdyPin)==1):
                pass
            adc = self.ISR()
            now_ts = time.time()-self.start_ts
            print now_ts, ((adc*12.000)/16777216.0)
            self.data_q.put((now_ts,adc))


    def join(self,_timeout=None):
        self.sample_On = False
        threading.Thread.join(self,_timeout)
        
'''
data_q = Queue.Queue()
adc = ADCMonitor(data_q,0)
adc.start()
time.sleep(10)
adc.join()
'''

