import select
import cipher
import socket

RECV_TIMEOUT_SEC = 20
NORMAL_PACKET_SIZE_BYTES = cipher.BLOCK_SIZE + 2 # 18 bytes = Flag(1byte) + Param(1Byte) + Payload(16Bytes)
NORMAL_PAYLOAD_SIZE_BYTES = cipher.BLOCK_SIZE # 16 bytes
PUB_KEY_PACKET_SIZE_BYTES = 66 # 66 bytes = Flag(1byte) + Param(1Byte) + Payload(64Bytes)
PUB_KEY_PAYLOAD_SIZE_BYTES = 64 # Payload(64Bytes)
###############FLAGS###############
PUB_KEY_FLAG = 1 # 0X01
FILE_NAME_FLAG = 2 # 0X02
IV_FLAG = 3 # 0X03
EOT_FLAG = 4 # 0X04
ACK_FLAG = 5 # 0X05
FULL_PAYLOAD_FLAG = 6 # 0X06
PARTIAL_PAYLOAD_FLAG = 7 # 0X07
###################################
PAYLOAD_PLACEHOLDER_BYTE = cipher.PAYLOAD_PLACEHOLDER_BYTE
PACKET_FLAG_INDEX = 0
PACKET_PARAM_INDEX = 1
PAYLOAD_STARTING_INDEX = 2



def sendAndConfirm(conn, packet, expectedFlag, expectedParam=None, recvPacketSize=NORMAL_PACKET_SIZE_BYTES):
    try:
       conn.sendall(packet)
    except:
        print("Error sendAndConfirm(): failed to send bytes.")
        return False 
    readable, _, _ = select.select([conn], [], [], RECV_TIMEOUT_SEC)
    if not readable:
        print("Error sendAndConfirm(): timeout on receiving ack.")
        return False
    packet = conn.recv(recvPacketSize)
    if(len(packet) != recvPacketSize):
        print(f"Error sendAndConfirm(): Reply packet has invalid size, {len(packet)}.")
    if packet[PACKET_FLAG_INDEX] != expectedFlag:
        print(f'Error sendAndConfirm(): expected flag {expectedFlag} but got {packet[PACKET_FLAG_INDEX]}.')
        return False
    if expectedParam != None and expectedParam != packet[PACKET_PARAM_INDEX]:
        print(f'Error sendAndConfirm(): expected param {expectedParam} but got {packet[PACKET_PARAM_INDEX]}.')
        return False
    return True
    
def recvAndAck(conn, expectedFlag = None, expectedParam = None, recvPacketSize=NORMAL_PACKET_SIZE_BYTES):
    readable, _, _ = select.select([conn], [], [], RECV_TIMEOUT_SEC)
    if not readable:
        print('Error recvAndAck(): timeout on recv.')
        return None
    packet = conn.recv(recvPacketSize)
    if(len(packet) != recvPacketSize):
        print(f'Error recvAndAck(): invalid packet size size, {len(packet)}.')
        return None
    if expectedFlag != None and packet[PACKET_FLAG_INDEX] != expectedFlag:
        print(f'Error recvAndAck(): expected {expectedFlag} flag but got {packet[PACKET_FLAG_INDEX]}.')
        return None
    if expectedParam != None and packet[PACKET_PARAM_INDEX] != expectedParam:
        print(f'Error recvAndAck(): expected param {expectedParam} but got {packet[PACKET_PARAM_INDEX]}.')
        return None
    param = packet[PACKET_FLAG_INDEX] if expectedParam == None else expectedParam
    ackPacket = bytes([ACK_FLAG, param]) + (NORMAL_PAYLOAD_SIZE_BYTES * PAYLOAD_PLACEHOLDER_BYTE)
    try:
        conn.sendall(ackPacket)
    except:
        print('Error recvAndAck(): failed to send ACK packet.')
        return None 
    return packet
    

def makePacket(flag, param=None, payloadBytes=None, payloadByteSize = NORMAL_PAYLOAD_SIZE_BYTES):
    packet = bytes([flag])
    packet += bytes([param]) if param != None else PAYLOAD_PLACEHOLDER_BYTE
    packet += payloadBytes if payloadBytes != None else (payloadByteSize * PAYLOAD_PLACEHOLDER_BYTE)
    return packet
    
def sendPubKey(conn, pubPoint):
    pubPointBytes = cipher.pubPointToBytes(pubPoint)
    if len(pubPointBytes) != PUB_KEY_PAYLOAD_SIZE_BYTES:
        print(f'Error sendPubKey(): expected {PUB_KEY_PAYLOAD_SIZE_BYTES} bytes but got {len(pubPointBytes)}')
        return False
    packet = makePacket(PUB_KEY_FLAG, payloadBytes=pubPointBytes)
    if not sendAndConfirm(conn, packet, ACK_FLAG, PUB_KEY_FLAG):
        print("Error sendPubKey(): failed to send pub key packet.")
        return False
    return True 

def sendFileName(conn, fileNameStr):
    fileNameBytes = fileNameStr.encode()
    paddedFileName, _ = cipher.padBytes(fileNameBytes, NORMAL_PAYLOAD_SIZE_BYTES)
    packet = makePacket(FILE_NAME_FLAG, len(fileNameBytes), paddedFileName)
    if not sendAndConfirm(conn, packet, ACK_FLAG, FILE_NAME_FLAG):
       print("Error sendFileName(): failed to send file name.")
       return False
    return True 

def sendIV(conn, ivBytes):
    #iv is exactly the same size as block size
    packet = makePacket(IV_FLAG, payloadBytes=ivBytes)
    if not sendAndConfirm(conn, packet, ACK_FLAG, IV_FLAG):
       print("Error sendIV(): failed to send IV.")
       return False
    return True
    
def sendEOT(conn):
   packet = makePacket(EOT_FLAG)
   if not sendAndConfirm(conn, packet, ACK_FLAG, expectedParam=EOT_FLAG):
      print("Error sendEOT(): failed to send EOT packet.")
      return False
   return True

def sendFullPayload(conn, fullpayload):
   packet = makePacket(FULL_PAYLOAD_FLAG, payloadBytes=fullpayload)
   if not sendAndConfirm(conn, packet, ACK_FLAG, FULL_PAYLOAD_FLAG):
      print("Error sendFullPayload(): failed to send a full payload.")
      return False
   return True

def sendPartialPayload(conn, paddedPayload, partialPayloadSize):
   packet = makePacket(PARTIAL_PAYLOAD_FLAG, partialPayloadSize, paddedPayload)
   if not sendAndConfirm(conn, packet, ACK_FLAG, expectedParam=PARTIAL_PAYLOAD_FLAG):
      print("Error sendPartialPayload(): failed to send a partial payload.")
      return False
   return True 

def getPubKey(conn):
    packet = recvAndAck(conn, PUB_KEY_FLAG, recvPacketSize=PUB_KEY_PACKET_SIZE_BYTES)
    if packet == None:
        print('Error getPubKey(): failed to recv public key packet')
        return None
    return cipher.bytesToPubPoint(packet[PAYLOAD_STARTING_INDEX:])

def getFileName(conn):
   packet = recvAndAck(conn, FILE_NAME_FLAG)
   if packet == None:
       print('Error getFileName(): failed to recv file name')
       return None
   fileNameBytes, _ = cipher.unpadBytes(packet[PAYLOAD_STARTING_INDEX:], packet[PACKET_PARAM_INDEX])
   fileNameStr = None
   try:
       fileNameStr = fileNameBytes.decode('utf-8')
   except:
       print("Error getFileName() failed to parse file name bytes to str.")
       return None
   return fileNameStr

def getIV(conn):
    packet = recvAndAck(conn, IV_FLAG)
    if packet == None:
        print('Error getIV(): failed to recv IV.')
        return None
    return packet[PAYLOAD_STARTING_INDEX:]
   

def getPacketDataStream(conn):
    packet = recvAndAck(conn)
    if packet == None:
       print('Error getPacketDataStream(): failed to recv packet.')
       return None
   
    parsedPacketDict = {'EOT_FLAG':False, 'PARTIAL_PAYLOAD_FLAG':False, 'FULL_PAYLOAD_FLAG':False}
    if packet[PACKET_FLAG_INDEX] == EOT_FLAG:
        parsedPacketDict['EOT_FLAG'] = True
    elif packet[PACKET_FLAG_INDEX] == PARTIAL_PAYLOAD_FLAG:
        parsedPacketDict['PARTIAL_PAYLOAD_FLAG'] = True
        parsedPacketDict['partialPayloadBytes'] = packet[PAYLOAD_STARTING_INDEX:]
        parsedPacketDict['partialPayloadSize'] = packet[PACKET_PARAM_INDEX]
    elif packet[PACKET_FLAG_INDEX] == FULL_PAYLOAD_FLAG:
        parsedPacketDict['FULL_PAYLOAD_FLAG'] = True
        parsedPacketDict['fullPayloadBytes'] = packet[PAYLOAD_STARTING_INDEX:]
    else:
        print('Error getPacketDataStream(): recv unrecognized packet type.')
        return None 
    return parsedPacketDict
    


 
def getIPv4Addr():
   with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as dummySocket:
      IPv4Addr = None
      try:
         dummySocket.connect(("8.8.8.8", 80))
         IPv4Addr = dummySocket.getsockname()[0]
      except Exception as e:
         print('Error getIPv4Addr(): failed to fetch this machine\' first IPv4 address:', str(e))
         return None
   return IPv4Addr

