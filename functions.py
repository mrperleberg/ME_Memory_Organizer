#import os
import math
import subprocess
from subprocess import PIPE

def generateFile(SRAMSizeFinal, blockSize, bankCount, readPorts, baseFile, tempFile):
	fnew = open(tempFile, "w")
	fnew.write("-size (bytes) " + str(SRAMSizeFinal) + "\n")
	fnew.write("-block size (bytes) " + str(blockSize) + "\n")
	fnew.write("-UCA bank count " + str(bankCount) + "\n")
	fnew.write("-exclusive read port " + str(readPorts) + "\n")
	fnew.write("-output/input bus width " + str(blockSize * 8) + "\n")
	fnew.write("\n\n\n")

	fbase = open(baseFile, "r")
	for line in fbase:
		fnew.write(line)

	fnew.close()
	fbase.close()

def runCfg(executableCacti, temporaryFile, outFile):
	cmd = executableCacti + " -infile " + temporaryFile + " \&> " + outFile

	proc = subprocess.Popen([cmd], stdout=subprocess.PIPE, stderr=PIPE, shell=True, text=True)
	(out, err) = proc.communicate()
	if err:
		if (	("Need to either increase cache size" in err) or 
				("Cache size must >=64" in err)
			):
			with open(outFile, "a") as fw:
				fw.write(err)
			return "errorSize"
		
		print("Not yet treated")
		print(err) 

def catchResults(outpu):
	fout = open(outpu, "r")
	
	accessTime = 0.0
	readEnergy = 0.0
	leakagePower = 0.0
	height = 0.0
	width = 0.0

	for line in fout:
		if "Access time (ns):" in line:
			accessTime = float(line.split(": ")[1].split("\n")[0])
		if "Total dynamic read energy" in line:
			readEnergy = float(line.split(": ")[1].split("\n")[0])
		if "Total leakage power of a bank" in line:
			leakagePower = float(line.split(": ")[1].split("\n")[0])
		if "Cache height x width" in line:
			height = float(line.split(": ")[1].split(" x ")[0])
			width = float(line.split(": ")[1].split(" x ")[1].split("\n")[0])
		if "ERROR: no valid data array organizations found" in line:
			return "errorSize"
		if "ERROR: no cache organizations met optimization criteria" in line:
			return "errorNoMetOptimization"
		if "Need to either increase cache size" in line:
			return "errorSize"
		if "Cache size must >=64" in line:
			return "errorSize"
	
	return [accessTime, readEnergy, leakagePower, height, width]

def runExtendingSRAMSize(cactiParameters, SRAMSizeBase, blockSize, bankCount, readPorts):
	executableCacti = cactiParameters["executavel"]
	baseFile = cactiParameters["baseFile"]
	temporaryFile = cactiParameters["temporaryFile"]
	outFile = cactiParameters["outFile"]

	SRAMSizeFinal = SRAMSizeBase
	tryAgain = True
	
	while (tryAgain):
		tryAgain = False
		
		generateFile(SRAMSizeFinal, blockSize, bankCount, readPorts, baseFile, temporaryFile)
		rodou = runCfg(executableCacti, temporaryFile, outFile)
		results = catchResults(outFile)

		if ((results == "errorSize") or (rodou == "errorSize")):
			if (SRAMSizeFinal <= 8*SRAMSizeBase):
				tryAgain = True
				SRAMSizeFinal = SRAMSizeFinal * 2
	
	return SRAMSizeFinal, results

def findReadPorts(band, SearchAreaWidth, blockSize, bankCount, CTUSize=64):
	#This function finds the minimal read port number to the given organization.
	bestReadPorts = SearchAreaWidth * band

	for blockWidth in range(SearchAreaWidth, 0, -1):
		blockHeight = blockSize / blockWidth
		if ((blockSize % blockWidth > 0) or (blockHeight == SearchAreaWidth + 1)):
			continue

		blocksNeededHeight = math.ceil((band + blockHeight - 1) / float(blockHeight))
		blocksNeededWidth = math.ceil((CTUSize + blockWidth - 1) / float(blockWidth * bankCount))

		readPorts = int(blocksNeededHeight * blocksNeededWidth)
		if (blockWidth == SearchAreaWidth):
			readPorts = int(blocksNeededHeight)
			
		readPorts = max(1, readPorts)

		bestReadPorts = min(bestReadPorts, readPorts)

	return bestReadPorts

def simulateOrganizations(cactiParameters, SRAMSizeBase, SearchAreaWidth, bandwidths, bankCounts, blockSizes, CTUSize=64, findBestReadPorts=True):
	dicts = []

	for band in bandwidths:
		for bankCount in bankCounts:
			for blockSize in blockSizes:

				if findBestReadPorts: 
					#Used on SRAM for Search Area
					readPorts = findReadPorts(band, SearchAreaWidth, blockSize, bankCount, CTUSize)
				else:
					#Used on SRAM for Current Block (which has regular memory accesses)
					readPorts = math.ceil((CTUSize*band / bankCount) / float(blockSize))

				SRAMSizeFinal, results = runExtendingSRAMSize(cactiParameters, SRAMSizeBase, blockSize, bankCount, readPorts)

				dataDict = {
					"SRAMSizeBase" : SRAMSizeBase,
					"band" : band,
					"SRAMSizeFinal" : SRAMSizeFinal,
					
					"blockSize (B)" : blockSize,
					"bankCount" : bankCount,
					"readPorts" : readPorts
				}
				
				if (results == "errorSize" or results == "errorNoMetOptimization"):
					dataDict["results"] = results
				else:
					dataDict["results"] = "ok"

					accessTime, readEnergy, leakagePower, height, width = results

					dataDict["accessTime (ns)"] = accessTime
					dataDict["height (mm)"] = height
					dataDict["width (mm)"] = width
					dataDict["area (mm2)"] = height * width
					dataDict["readEnergy (nJ)"] = readEnergy
					dataDict["bankPower (mW)"] = leakagePower
					dataDict["leakagePower (mW)"] = bankCount * dataDict["bankPower (mW)"]

				dicts.append(dataDict)
	return dicts
