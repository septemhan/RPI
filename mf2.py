# Import required libraries
import sys
import time
import RPi.GPIO as GPIO

# Use BCM GPIO references
# instead of physical pin numbers
#GPIO.setmode(GPIO.BCM)
mode=GPIO.getmode()
print " mode ="+str(mode)
GPIO.cleanup()

# Define GPIO signals to use
# Physical pins 11,15,16,18
# GPIO17,GPIO22,GPIO23,GPIO24

StepSpeed=37
LEDPin = 7
StepPinForward=38
StepPinBackward=40

StepPinForwardB=33
StepPinBackwardB=31
StepBSpeed = 35

GPIO.setmode(GPIO.BOARD)
GPIO.setup(StepPinForward, GPIO.OUT)
GPIO.setup(StepPinBackward, GPIO.OUT)
GPIO.setup(StepPinForwardB, GPIO.OUT)
GPIO.setup(StepPinBackwardB, GPIO.OUT)
GPIO.setup(StepSpeed, GPIO.OUT)

global p

p = GPIO.PWM(37, 100)
p.start(70)

def forward(x):
    p.ChangeDutyCycle(70)
    GPIO.output(StepPinForward, GPIO.HIGH)
    print "forwarding running  motor "
    time.sleep(x)
    GPIO.output(StepPinForward, GPIO.LOW)

def reverse(x):
    GPIO.output(StepPinBackward, GPIO.HIGH)
    print "backwarding running motor"
    time.sleep(x)
    GPIO.output(StepPinBackward, GPIO.LOW)

forward(3)
