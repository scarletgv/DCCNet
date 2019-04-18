# -*- coding: utf-8 -*-
"""
Spyder Editor

Este é um arquivo de script temporário.
"""

def encode16( hexData ):
    
    binData = []
    
    for index, byte in enumerate(hexData):
            binData.append(hex(ord(byte[0])).lstrip('0x'))
            binData.append(hex(ord(byte[1])).lstrip('0x'))
    return binData

def decode16 ( binData ):
    
    hexData = []
    
    for i in range(1,len(binData),2):
        c1 = chr(int(binData[i-1],16))
        c2 = chr(int(binData[i],16))
        hexData.append(c1+c2)
    return hexData

hexFrame = ['cc','00','7f','ae','2d','01','02','03','04','cd']
htob = encode16(hexFrame)
print(htob)

btoh = decode16(htob)
print(btoh)

