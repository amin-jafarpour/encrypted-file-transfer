import cipher
import matplotlib.pyplot as plt # type: ignore


SINGLE_BLOCK_SIZE_BYTES = 16
NUMBER_OF_FISTEL_ROUNDS = 16


def graph(bitDiffList, savePath, color, title):
   barLabels = list(map(lambda x: f'R{x}', range(1,NUMBER_OF_FISTEL_ROUNDS + 1)))
   plt.bar(barLabels, bitDiffList, width=0.4, color=color)
   for index, value in enumerate(bitDiffList):
      plt.text(index, value + 1, str(value), ha='center')
      
   plt.xlabel('Round Number')
   plt.ylabel('Number of Differing Bits')
   plt.title(title)
   plt.grid(True)
   plt.savefig(savePath) 
   plt.clf()
   plt.cla()
   

def getEncryptionRounds(plainBlock, mainkey):
   subKeyList = cipher.deriveSubkeys(mainkey)
   leftSide, rightSide = plainBlock[:cipher.HALF_BLOCK_SIZE], plainBlock[cipher.HALF_BLOCK_SIZE:]
   assert(len(leftSide) == len(rightSide) == cipher.HALF_BLOCK_SIZE)
   roundsValue = []
   for subKey in subKeyList:
      leftSide, rightSide = cipher.fistelRound(leftSide, rightSide, subKey)
      roundsValue.append(leftSide + rightSide)
   assert(len(roundsValue) == cipher.FISTEL_ROUND_COUNT)
   return roundsValue
    
    
def countBitDiff(bytes1, bytes2):
   assert(len(bytes1) == len(bytes2) == SINGLE_BLOCK_SIZE_BYTES)
   
   int1 = int.from_bytes(bytes1, byteorder='big')
   int2 = int.from_bytes(bytes2, byteorder='big')
   
   xoredResult = int1 ^ int2
   bitDiffCount = bin(xoredResult).count('1')
   
   return bitDiffCount


def SPAC(originalPlaintextInt, modifiedPlaintextInt, mainkeyint, imgSavePath):
    originalPlaintextBytes = originalPlaintextInt.to_bytes(SINGLE_BLOCK_SIZE_BYTES)
    modifiedPlaintextBytes = modifiedPlaintextInt.to_bytes(SINGLE_BLOCK_SIZE_BYTES)
    mainkeyBytes = mainkeyint.to_bytes(SINGLE_BLOCK_SIZE_BYTES)
    assert(len(originalPlaintextBytes) == len(modifiedPlaintextBytes) == len(mainkeyBytes) == SINGLE_BLOCK_SIZE_BYTES)
    
    originalList = getEncryptionRounds(originalPlaintextBytes, mainkeyBytes)
    modifiedList = getEncryptionRounds(modifiedPlaintextBytes, mainkeyBytes)
    
    bitDiffPerRound = [countBitDiff(original, modified) for original, modified in zip(originalList, modifiedList)]
    graph(bitDiffPerRound, imgSavePath, 'blue', 'SPAC: Differing Bits Per Round Number')
    return bitDiffPerRound
    
    
def SKAC(originalPlaintextInt, originalMainkeyInt, modifiedMainkeyInt, imgSavePath):
   originalPlaintextBytes = originalPlaintextInt.to_bytes(SINGLE_BLOCK_SIZE_BYTES)
   originalMainkeyBytes = originalMainkeyInt.to_bytes(SINGLE_BLOCK_SIZE_BYTES)
   modifiedMainkeyBytes= modifiedMainkeyInt.to_bytes(SINGLE_BLOCK_SIZE_BYTES)
   assert(len(originalPlaintextBytes) == len(originalMainkeyBytes) == len(modifiedMainkeyBytes) == SINGLE_BLOCK_SIZE_BYTES)
   
   originalList = getEncryptionRounds(originalPlaintextBytes, originalMainkeyBytes)
   modifiedList = getEncryptionRounds(originalPlaintextBytes, modifiedMainkeyBytes)
   
   bitDiffPerRound = [countBitDiff(original, modified) for original, modified in zip(originalList, modifiedList)]
   graph(bitDiffPerRound, imgSavePath, 'red', 'SKAC: Differing Bits Per Round Number')
   return bitDiffPerRound
    

def generateAvalancheEffectGraphs():
    
    originalPlaintextInt = 0xcb58dc99fb1496a1e6d5ec09453aa801
    originalMainkeyInt = 0xe5f10672c7e7aaa2f23077c249f20f91
    assert(len(hex(originalPlaintextInt)) == len(hex(originalMainkeyInt)) == 34)
    
    print(f'Original Plaintext in hex = {hex(originalPlaintextInt)}')
    print(f'Original Main Key in hex = {hex(originalMainkeyInt)}')
    
    # SPAC: changing 1 bit of plaintext
    modifiedPlaintextInt1 = 0xcb58dc99fb1496a1e6d5ec09453aa802
    print('SPAC: changing 1 bit of plaintext:')
    print(f'Modified plaintext with 1 bit change = {hex(modifiedPlaintextInt1)}')
    bitDiff = SPAC(originalPlaintextInt, modifiedPlaintextInt1, originalMainkeyInt, './SPAC_1bit.png')
    print(f'SPAC 1bit: Count of differing bits rounds 1-16: {bitDiff}')
    
    
   # SPAC: changing 2 bit of plaintext
    modifiedPlaintextInt2 = 0xcb58dc99fb1496a1e6d5ec09453aa803
    print('SPAC: changing 2 bit of plaintext:')
    print(f'Modified plaintext with 2 bit change = {hex(modifiedPlaintextInt2)}')
    bitDiff = SPAC(originalPlaintextInt, modifiedPlaintextInt2, originalMainkeyInt, './SPAC_2bit.png')
    print(f'SPAC 2bit: Count of differing bits rounds 1-16: {bitDiff}')
    
    # SKAC: changing 1 bit of main key
    modifiedMainkeyInt1 = 0xe5f10672c7e7aaa2f23077c249f20f92
    print('SKAC: changing 1 bit of main key:')
    print(f'Modified main key with 1 bit change = {hex(modifiedMainkeyInt1)}')
    bitDiff = SKAC(originalPlaintextInt, originalMainkeyInt, modifiedMainkeyInt1, './SKAC_1bit.png')
    print(f'SKAC 1bit: count of bits rounds 1-16: {bitDiff}')
    
    
    # SKAC: changing 2 bit of main key
    modifiedMainkeyInt2 = 0xe5f10672c7e7aaa2f23077c249f20f93
    print('SKAC: changing 2 bit of main key:')
    print(f'Modified main key with 2 bit change = {hex(modifiedMainkeyInt2)}')
    bitDiff = SKAC(originalPlaintextInt, originalMainkeyInt, modifiedMainkeyInt2, './SKAC_2bit.png')
    print(f'SKAC 2bit: count of bits rounds 1-16: {bitDiff}')
    
    
    

def main():
   generateAvalancheEffectGraphs()
   
   
   
if __name__ == "__main__":
   main()
    
    
    
   
    
    
    
    
    
    
    
    
    
    
   