#!/usr/bin/python
# macgen.py script to generate a MAC address for guests
#
# Any domain specific MAC rules can be added to this generic example
#
import random
#
def randomMAC():
	mac = [ 0x00, 0x16, 0x3e,
		random.randint(0x00, 0x7f),
		random.randint(0x00, 0xff),
		random.randint(0x00, 0xff) ]
	return ':'.join(map(lambda x: "%02x" % x, mac))
#
print randomMAC()