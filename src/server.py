import cipher
import networking
import socket
import threading
import os
import argparse
import sys


SERVER_VERBOSITY_LOW = 1
SERVER_VERBOSITY_MEDIUM = 2 
SERVER_VERBOSITY_HIGH = 3
currentServerVerbosity = SERVER_VERBOSITY_LOW

def printInfoServer(info, verbosityLevel=SERVER_VERBOSITY_LOW):
   if currentServerVerbosity >= verbosityLevel:
      print(f"{info}")
   
def startListening(port):
   hostName = socket.gethostname()
   hostIPv4 = networking.getIPv4Addr() # socket.gethostbyname(hostName)
   
   printInfoServer("server's host name " + hostName)
   printInfoServer("server's IPv4 address " + hostIPv4)
   conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   
   conn.bind((hostIPv4, port))
   conn.listen()
   return conn 


def initClientSession(cliCon, clientIPv4):
   # get client public key 
   if (cliPubKeyPoint := networking.getPubKey(cliCon)) == None:
      print('Error initClientSession(): failed to get client public key.')
      return None
   
   #generate private-public key pairs for the server
   priKey, pubKeyPoint = cipher.generatePrivPubKeys()
    
   #send server's public key to client
   if networking.sendPubKey(cliCon, pubKeyPoint) == False:
      print("Error initClientSession(): failed to send public key to client.")
      return None
   
   # derive shared secret
   sharedSecret = cipher.deriveSymmetricSessionKey(priKey, cliPubKeyPoint)
   
   # get file name from client  
   if (fileName := networking.getFileName(cliCon)) == None:
      print('Error initClientSession(): failed to get file name from client.')
      return None
   
   # get IV client used for encryption
   if (iv := networking.getIV(cliCon)) == None:
      print('Error initClientSession(): failed to get IV from client.')
      return None
   
   #print info
   printInfoServer(f'{clientIPv4} server\'s private key: {priKey}', SERVER_VERBOSITY_MEDIUM)
   printInfoServer(f'{clientIPv4} server\'s public key: ({pubKeyPoint.x}, {pubKeyPoint.y})', SERVER_VERBOSITY_MEDIUM)
   printInfoServer(f'{clientIPv4} client\'s public key: ({cliPubKeyPoint.x, {cliPubKeyPoint.y}})', SERVER_VERBOSITY_MEDIUM)
   printInfoServer(f'{clientIPv4} session\'s sharedSecret: {sharedSecret}', SERVER_VERBOSITY_MEDIUM)
   printInfoServer(f'{clientIPv4} fileName: {fileName}', SERVER_VERBOSITY_MEDIUM)
   printInfoServer(f'{clientIPv4} IV: {iv}', SERVER_VERBOSITY_MEDIUM)
   
   # generate subkeys for each individual Fistel round
   subKeyList = cipher.deriveSubkeys(sharedSecret)
   return {"fileName": fileName, "iv":iv, "subKeyList": subKeyList}
   


def handleClient(cliCon, cliAddr, fileStorePath):
   
    clientIPv4, clientPort = cliAddr
    #print("Connected client IP:", cliAddr)
    printInfoServer(f'client {clientIPv4} connected from port {clientPort}', SERVER_VERBOSITY_MEDIUM)
    
    #print public keys, peer IP, Sequence number, decrypted text.
    if (sessionParams := initClientSession(cliCon, clientIPv4)) == None:
       printInfoServer("Error handleClient(): failed to init session. Terminating.")
       cliCon.close()
       return 
     
     
     
    subKeyList = sessionParams['subKeyList']
    previousCipherBlock = sessionParams['iv'] 
    fullFilePath = os.path.join(fileStorePath, sessionParams['fileName'])
    
    sequenceNum = 0
    with open(fullFilePath, "wb") as file:
      while True:
         parsedPacketDict = networking.getPacketDataStream(cliCon)
         # holds the current encrypted data block
         cipherBlock = None
         
         if parsedPacketDict == None:
            print('Error handleClient(): failed to recv valid packet. Terminating session.')
            cliCon.close()
            return
         
         # if terminating EOT packet recv,
         if parsedPacketDict['EOT_FLAG']:
             printInfoServer("recevied EOT packet from client", SERVER_VERBOSITY_MEDIUM)
             # stop waiting for client packets
             break
            
         # if recv a partial payload packet,
         elif parsedPacketDict['PARTIAL_PAYLOAD_FLAG']:
            cipherBlock = parsedPacketDict['partialPayloadBytes']
          
         # if recv a full payload packet,  
         elif parsedPacketDict['FULL_PAYLOAD_FLAG']:
            cipherBlock = parsedPacketDict['fullPayloadBytes']
         
         # decrypt the current cipher block
         decryptedBlock = cipher.decryptBlockCBC(cipherBlock, previousCipherBlock, subKeyList)
         
         # removing the padding after decryption if packet recv was partial
         if parsedPacketDict['PARTIAL_PAYLOAD_FLAG']:
            
            decryptedBlock, _ = cipher.unpadBytes(decryptedBlock, parsedPacketDict['partialPayloadSize'])
            
         
         # store current cipher block for decrypting the next block
         previousCipherBlock = cipherBlock
   
         printInfoServer(f'recv from {cliAddr} block number# {(sequenceNum := (sequenceNum + 1))}: {decryptedBlock}', SERVER_VERBOSITY_HIGH)
         
         bytesWritten = file.write(decryptedBlock)
         if len(decryptedBlock) > bytesWritten:
            print("Error handleClient(): failed to write all bytes content to file.")
            cliCon.close()
            return
    printInfoServer(f"Client {cliAddr} request to close the session. Closing the session.", SERVER_VERBOSITY_MEDIUM)
    cliCon.close()
    
   
def acceptClient(conn, storePath):
    printInfoServer('accepting clients now ...',SERVER_VERBOSITY_MEDIUM)
    while True:
       cliCon, cliAddr = conn.accept()
       threadCli = threading.Thread(target=handleClient, args=(cliCon, cliAddr, storePath))
       threadCli.start()
       #threadCli.join()
           
   
def makeClientCMDParser():
     parser = argparse.ArgumentParser(description="...")
     parser.add_argument('-sp', '--serverport', help='Port number to run server on.', type=int, required=True)
     parser.add_argument('-sd', '--savedirectory', help='Path of directory where files are stored..', type=str, required=True)
     parser.add_argument('-v', '--verbosity', help='verbosity level: low(l), medium(m), high(h)', type=str)
     return parser.parse_args()
  
  
def startServer(port, storePath):
   conn = startListening(port)
   acceptClient(conn, storePath)
   conn.close()
   
def main():
   CMDArgs = makeClientCMDParser()
   
   verbositiy = CMDArgs.verbosity
   verbositiyNumeric = None
   if verbositiy != None and verbositiy.strip() != '':
      verbositiy = verbositiy.lower()
      if verbositiy in ['h', 'high']:
         verbositiyNumeric = SERVER_VERBOSITY_HIGH
      elif verbositiy in ['m', 'medium']:
         verbositiyNumeric = SERVER_VERBOSITY_MEDIUM
      elif verbositiy in ['l', 'low']:
         verbositiyNumeric = SERVER_VERBOSITY_LOW
      else:
         print('invalid value for --verbosity(-v) option given:', verbositiy)
         sys.exit(1)
   else:
      print('no value given for--verbosity(-v) option given. Using default low(l) verbosity level')
      verbositiyNumeric = SERVER_VERBOSITY_LOW
      
   global currentServerVerbosity      
   currentServerVerbosity = verbositiyNumeric
   print(f'Running server.py with verbositiy level set to {['', 'low', 'medium', 'high'][currentServerVerbosity]}')
   
   startServer(CMDArgs.serverport, CMDArgs.savedirectory)
   
   
if __name__ == "__main__":
   main()