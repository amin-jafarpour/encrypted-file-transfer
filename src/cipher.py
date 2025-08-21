import secrets
import hashlib
from tinyec import registry # type: ignore
import os
import tinyec.ec # type: ignore
import random
from Crypto.Util.Padding import pad, unpad # type: ignore
import argparse
import re
import secrets

# key size = 128 bits
# block size = 128 bits
# 16 Fistel rounds
# strong round function

BITS_PER_BYTE = 8
BLOCK_SIZE = 16 # 128 bits / 1 Bytes = 16 Bytes
HALF_BLOCK_SIZE = 8
FISTEL_ROUND_COUNT = 16
ECC_CURVE = registry.get_curve("brainpoolP256r1")
PAYLOAD_PLACEHOLDER_BYTE = bytes([2])
ECC_CORD_SIZE_BYTES = 32
HALF_BLOCK_SIZE_BIT_COUNT = HALF_BLOCK_SIZE * BITS_PER_BYTE


DEFAULT_BMP_IMAGE_HEADER_SIZE = 54

def padBytes(dataBytes, blockSizeBytes, padBytes = PAYLOAD_PLACEHOLDER_BYTE):
    if len(dataBytes) > blockSizeBytes:
        raise Exception("dataBytes is greater than blockSizeBytes")
    padCount = blockSizeBytes - len(dataBytes)
    return (dataBytes + (padCount * padBytes), padCount)

def unpadBytes(paddedDataBytes, actualDataSizeBytes):
    if len(paddedDataBytes) < actualDataSizeBytes:
        raise Exception("paddedDataBytes is less than actualDataSizeBytes")
    return (paddedDataBytes[:actualDataSizeBytes], len(paddedDataBytes) - actualDataSizeBytes)
 
 
def deriveSymmetricSessionKey(selfPrivKey, peerPubKey, symmetricKeySize=BLOCK_SIZE):
   sharedPoint = selfPrivKey * peerPubKey
   cordXORed = sharedPoint.x ^ sharedPoint.y
   bitLength = (sharedPoint.x.bit_length()+ 7) // 8
   cordXORedBytes = cordXORed.to_bytes(bitLength, 'big')
   symmetricKey = hashlib.sha256(cordXORedBytes).digest()[:symmetricKeySize]
   return symmetricKey

def generatePrivPubKeys():
   privKey = secrets.randbelow(ECC_CURVE.field.n)
   pubKey = privKey * ECC_CURVE.g
   return (privKey, pubKey)

def permutate(inputBytes):
   assert(len(inputBytes) == HALF_BLOCK_SIZE)
   
   hashDigest = (hashlib.sha256(inputBytes)).digest()
   seed = int.from_bytes(hashDigest[:HALF_BLOCK_SIZE], 'big')
   random.seed(seed)
   bitPositions = list(range(1, HALF_BLOCK_SIZE * BITS_PER_BYTE + 1))
   random.shuffle(bitPositions)
   #...
   inputBytesInt = int.from_bytes(inputBytes, 'big')
   acc = 0b0
   for i, pos in enumerate(bitPositions):
      mask = (0b1 << (pos - 1))
      bitVal = int(bool(mask & inputBytesInt))
      acc |= (bitVal << i)
   
   res = acc.to_bytes(HALF_BLOCK_SIZE, byteorder='big')
   return res
      
def roundFunc(rightSide, roundKey): 
   assert(len(rightSide) == len(roundKey) == HALF_BLOCK_SIZE)
   XORed = bytes([x ^ y for x, y in zip(rightSide, roundKey)])
   return permutate(XORed)
   
def fistelRound(leftSide, rightSide, roundKey):
   roundFuncResult = roundFunc(rightSide, roundKey)
   newRightside = bytes([leftSide[i] ^ roundFuncResult[i] for i in range(HALF_BLOCK_SIZE)])
   newLeftSide = rightSide
   return (newLeftSide, newRightside)

def deriveSubkeys(sessionKey, subkeyCount=FISTEL_ROUND_COUNT, subkeySize=HALF_BLOCK_SIZE):
   assert(len(sessionKey) == BLOCK_SIZE)
   subkeysList = []
   for i in range(subkeyCount):
      hashData = sessionKey + i.to_bytes(subkeySize, 'big')
      hashDigest = hashlib.sha256(hashData).digest()
      subkey = hashDigest[:subkeySize] 
      subkeysList.append(subkey)
   return subkeysList
      
      
def encryptBlock(plainBlock, subKeyList):
   leftSide, rightSide = plainBlock[:HALF_BLOCK_SIZE], plainBlock[HALF_BLOCK_SIZE:]
   assert(len(leftSide) == len(rightSide) == HALF_BLOCK_SIZE)
   for subKey in subKeyList:
      leftSide, rightSide = fistelRound(leftSide, rightSide, subKey)
   return leftSide + rightSide

def decryptBlock(encryptedBlock, subKeyList):
   leftSide, rightSide = encryptedBlock[:HALF_BLOCK_SIZE], encryptedBlock[HALF_BLOCK_SIZE:]
   assert(len(leftSide) == len(rightSide) == HALF_BLOCK_SIZE)
   for subKey in reversed(subKeyList):
      rightSide, leftSide = fistelRound(rightSide, leftSide, subKey)
   return leftSide + rightSide


def encryptBlockCBC(plainBlock, previousBlock, subKeyList):
   currentBlockXORED = bytes([plainBlock[i] ^ previousBlock[i] for i in range(BLOCK_SIZE)])
   encryptedBlock = encryptBlock(currentBlockXORED, subKeyList)
   return encryptedBlock
   
def decryptBlockCBC(cipherBlock, previousBlock, subKeyList):
   transformedBlock = decryptBlock(cipherBlock, subKeyList)
   decryptedBlock = bytes([transformedBlock[i] ^ previousBlock[i] for i in range(BLOCK_SIZE)])
   return decryptedBlock
   
   
def generateIV(blockSize=BLOCK_SIZE):
   return os.urandom(blockSize)

def pubPointToBytes(pubPoint):
   xBytes = pubPoint.x.to_bytes(ECC_CORD_SIZE_BYTES, 'big')
   yBytes = pubPoint.y.to_bytes(ECC_CORD_SIZE_BYTES, 'big')
   return xBytes + yBytes
      
def bytesToPubPoint(pubPointBytes):
   x = int.from_bytes(pubPointBytes[:ECC_CORD_SIZE_BYTES], 'big')
   y = int.from_bytes(pubPointBytes[ECC_CORD_SIZE_BYTES:], 'big')
   return tinyec.ec.Point(ECC_CURVE, x, y)
   

def makeClientCMDParser():
     parser = argparse.ArgumentParser(description="...")
     parser.add_argument('-op', '--operation', help='', type=str, required=True)
     parser.add_argument('-in', '--input', help='', type=str, required=True)
     parser.add_argument('-out', '--output', help='', type=str, required=True)
     parser.add_argument('-k', '--mainkey', help='', type=str, required=False)
     parser.add_argument('-iv', '--iv', help='', type=str, required=False)
     parser.add_argument('-hs', '--headersize', help='', type=int, required=False)
     return parser.parse_args()
  


def cipherOperation():
   parser = makeClientCMDParser()
   
   headerSizeBytes = DEFAULT_BMP_IMAGE_HEADER_SIZE
   
   if parser.headersize != None and parser.headersize >= 0:
      headerSizeBytes = parser.headersize
      
   print(f'Header size selected is {headerSizeBytes} Bytes. The header section of file will not be encrypted/decrypted')
   
   
   operation = parser.operation
   inputFilePath = parser.input
   outputFilePath = parser.output
   mainkeyStr = parser.mainkey
   ivStr = parser.iv
   
   
   if operation.lower() not in ['e', 'encrypt', 'd', 'decrypt']:
      print('Error cipherOperation(): invalid operation value:', operation)
      return None 
   
   isEncrypting = True if operation.lower() in ['e', 'encrypt'] else False
   
   if isEncrypting and mainkeyStr == None:
      mainkeyStr = '0x' + ''.join(secrets.choice('0123456789abcdef') for _ in range(32))
      print('Main Key:', mainkeyStr)
      
   elif mainkeyStr == None or not bool(re.fullmatch(r'0[xX][0-9A-Fa-f]{32}', mainkeyStr)):
      print('Error cipherOperation(): mainkey is not valid:', mainkeyStr)
      return None
   
   if isEncrypting and ivStr == None:
      ivStr = '0x' + ''.join(secrets.choice('0123456789abcdef') for _ in range(32))
      print('IV used:', ivStr)
   elif ivStr == None or not bool(re.fullmatch(r'0[xX][0-9A-Fa-f]{32}', ivStr)):
      print('Error cipherOperation(): IV is not valid:', ivStr)
      return None
   
   operationFunc = encryptBlockCBC if isEncrypting else decryptBlockCBC
   previousCipherBlock = bytes.fromhex(ivStr[2:])
   mainkey = bytes.fromhex(mainkeyStr[2:])
   subkeyList = deriveSubkeys(mainkey)
  
   
   readBytes = None
   privReadBytes = None
   transBlock = bytes()
   if True:
  
      with open(inputFilePath, 'rb') as reader, open(outputFilePath, 'wb') as writer:
         
         # write header 
         writer.write(reader.read(headerSizeBytes))
         
         
         while True: 
            if len(readBytes := reader.read(BLOCK_SIZE)) != BLOCK_SIZE:
               break
            privReadBytes = readBytes
         
            # write previous block
            writer.write(transBlock)
            
            transBlock = operationFunc(readBytes, previousCipherBlock, subkeyList)
            previousCipherBlock = transBlock if isEncrypting else readBytes
            assert(len(transBlock) == len(readBytes))
            
            
         if isEncrypting:
            assert(len(transBlock) == BLOCK_SIZE)
            writer.write(transBlock)
            assert(len(readBytes) < BLOCK_SIZE)
            writer.write(pad(readBytes, BLOCK_SIZE))
            
            
         if not isEncrypting:
            assert(len(readBytes) == 0)
            writer.write(unpad(privReadBytes,BLOCK_SIZE))
     
   
            
         
            
   
      
def main():
   cipherOperation()

      
if __name__ == "__main__":
   main()

   
   
   
 
   