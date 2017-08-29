import threading
On = True

def doISR():
    while (On==True):
        while (wp.digitalRead(DrdyPin)==1):
            c=1
        Adc = ISR(0)   #ch1 is for EC module 
        #print((Adc * 100 ) / 167 / 1000000.0)
        I = ((Adc*12.000)/16777216.0)
        print I

def dowork():
    print '111'


class adc_thread(threading.Thread):
    def __init__(self,th_id,name):
        threading.Thread.__init__(self)
        self.id = th_id
        self.name = name

    def run(self):
        #doISR()
        dowork()


t_adc = adc_thread(1,'adc1')
t_adc.start()
