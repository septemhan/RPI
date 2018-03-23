import picamera
import time
camera = picamera.PiCamera()
camera.resolution = (1024,768)
camera.start_preview()
time.sleep(2)
#camera.capture('foo.jpg')
