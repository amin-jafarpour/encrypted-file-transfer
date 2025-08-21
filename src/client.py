import socket
import argparse
import cipher
import networking
import threading
import os
import sys

CLIENT_VERBOSITY_LOW = 1
CLIENT_VERBOSITY_MEDIUM = 2 
CLIENT_VERBOSITY_HIGH = 3
currentClientVerbosity = CLIENT_VERBOSITY_LOW

def printInfoServer(info, verbosityLevel=CLIENT_VERBOSITY_LOW):
   if currentClientVerbosity >= verbosityLevel:
      print(f"Client: {info}")
      
def connectToServer(serverIPv4, serverPort):
   conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   conn.connect((serverIPv4, serverPort))
   return conn
   


def transferFile(conn, symmetricKey, iv, fileName):
   subkeysList = cipher.deriveSubkeys(symmetricKey)
   previousCipherBlock = iv
   with open(fileName, "rb") as file:
      dataBlockBytes = file.read(cipher.BLOCK_SIZE)
      while len(dataBlockBytes) != 0:
         
         printInfoServer(f'sending block: {dataBlockBytes}', CLIENT_VERBOSITY_HIGH)
         
         paddedBlockBytes = dataBlockBytes
         if len(dataBlockBytes) != cipher.BLOCK_SIZE:
             paddedBlockBytes, _ = cipher.padBytes(dataBlockBytes, cipher.BLOCK_SIZE)
             
         paddedEncryptedBlock = cipher.encryptBlockCBC(paddedBlockBytes, previousCipherBlock, subkeysList)
         previousCipherBlock = paddedEncryptedBlock
         assert(len(paddedEncryptedBlock) == len(paddedBlockBytes))
         
         sendStatus = False
         if len(dataBlockBytes) < networking.NORMAL_PAYLOAD_SIZE_BYTES:
            sendStatus = networking.sendPartialPayload(conn, paddedEncryptedBlock, len(dataBlockBytes))
         else:
            sendStatus = networking.sendFullPayload(conn, paddedEncryptedBlock)
             
         if not sendStatus:
            print("Error transferFile(): failed to send data packet to server.")
            return False
         
         dataBlockBytes = file.read(cipher.BLOCK_SIZE)
   return True
        
def startClient(serverIPv4, serverPort, fileName):
   #print public keys, peer IP, Sequence number.
    conn = connectToServer(serverIPv4, serverPort)
        
    priv, pub = cipher.generatePrivPubKeys()
    
    if not networking.sendPubKey(conn, pub):
       print('Error startClient(): failed to send public key to server.')
       conn.close()
       return False
    
    if (serverPubKeyPoint := networking.getPubKey(conn)) == None:
       print('Error startClient(): failed to receive server public key.')
       conn.close()
       return False
    
    sharedSecret = cipher.deriveSymmetricSessionKey(priv, serverPubKeyPoint)
  
    
    if not networking.sendFileName(conn, os.path.basename(fileName)):
        print('Error startClient(): failed to send file name to server.')
        conn.close()
        return False
     
    iv = cipher.generateIV()
    if not networking.sendIV(conn, iv):
        print('Error startClient(): failed to send IV to server.')
        conn.close()
        return False
     
    printInfoServer(f'Connected to server {serverIPv4} listening on {serverPort}')
    printInfoServer(f'client\'s private key: {priv}', CLIENT_VERBOSITY_MEDIUM)
    printInfoServer(f'client\'s public key: ({pub.x}, {pub.y})', CLIENT_VERBOSITY_MEDIUM)
    printInfoServer(f'server\'s public key: ({serverPubKeyPoint.x}, {serverPubKeyPoint.y})', CLIENT_VERBOSITY_MEDIUM)
    printInfoServer(f'shared secret: {sharedSecret}', CLIENT_VERBOSITY_MEDIUM)
    printInfoServer(f'sending file: {os.path.basename(fileName)}', CLIENT_VERBOSITY_MEDIUM)
    printInfoServer(f'Using IV: {iv}', CLIENT_VERBOSITY_MEDIUM)
    printInfoServer(f'initing a thread to perform file transfer...', CLIENT_VERBOSITY_MEDIUM)
     
    thread = threading.Thread(target=lambda: transferFile(conn, sharedSecret, iv, fileName))
    thread.start()
    thread.join()
   
    if not networking.sendEOT(conn):
        print('Error startClient(): failed to send EOT to server.')
        conn.close()
        return False
     
    printInfoServer(f'send EOT packet to server. Terminating the session.')
    conn.close()
    return True
    
    
def makeClientCMDParser():
     parser = argparse.ArgumentParser(description="...")
     parser.add_argument('-sa', '--serveraddress', help='Server IPv4 Address.', type=str, required=True)
     parser.add_argument('-sp', '--serverport', help='Server port number.', type=int, required=True)
     parser.add_argument('-fp', '--filepath', help='Path of file to transfer.', type=str, required=True)
     parser.add_argument('-v', '--verbosity', help='verbosity level: low(l), medium(m), high(h)', type=str)
     return parser.parse_args()
    
def main():
    CMDArgs = makeClientCMDParser()
    verbositiy = CMDArgs.verbosity
    verbositiyNumeric = None
    if verbositiy != None and verbositiy.strip() != '':
      verbositiy = verbositiy.lower()
      if verbositiy in ['h', 'high']:
         verbositiyNumeric = CLIENT_VERBOSITY_HIGH
      elif verbositiy in ['m', 'medium']:
         verbositiyNumeric = CLIENT_VERBOSITY_MEDIUM
      elif verbositiy in ['l', 'low']:
         verbositiyNumeric = CLIENT_VERBOSITY_LOW
      else:
         print('invalid value for --verbosity(-v) option given:', verbositiy)
         sys.exit(1)
    else:
      print('no value given for--verbosity(-v) option given. Using the default value low(l)')
      verbositiyNumeric = CLIENT_VERBOSITY_LOW
   
    global currentClientVerbosity   
    currentClientVerbosity = verbositiyNumeric
    print(f'Running client.py with verbositiy level set to {['', 'low', 'medium', 'high'][currentClientVerbosity]}')
   
    
    startClient(CMDArgs.serveraddress, CMDArgs.serverport, CMDArgs.filepath)
   
    
    
    
if __name__ == "__main__":
   main()