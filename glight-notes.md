
# Device IDs

ID 046d:c084 Logitech G203 Mouse
ID 046d:c336 Logitech G213 Keyboard


bmRequestType

       0b10100001
       
0x21 = 0b00100001
         76543210
            :::::..Recipient
          ::......Type
         :.........Data Phase Transfer Direction
         
         Recipient=Device
         Type=Class
         DPTD=Host-to-Device
         
         
       0b100100001
       
       
https://superuser.com/questions/873896/wireshark-usb-traces-explanations

https://github.com/walac/pyusb/blob/master/docs/tutorial.rst

https://julien.danjou.info/blog/2012/logitech-k750-linux-support

http://www.beyondlogic.org/usbnutshell/usb1.shtml

https://github.com/vpelletier/python-libusb1
https://falsinsoft.blogspot.de/2015/02/asynchronous-bulk-transfer-using-libusb.html

https://stackoverflow.com/questions/38779019/python-libusb1-asynchronous-transfer-no-device-status-just-after-successful-syn