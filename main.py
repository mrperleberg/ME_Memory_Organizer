import numpy as np

import pickle
import pandas as pd
import math

import functions as sCacti

np.set_printoptions(
	edgeitems=10,
	linewidth = 100
)

cactiFolder = "./cacti/"
cactiParameters = {
	"executavel" : cactiFolder+"cacti",
	"baseFile" : cactiFolder+"BASE.cfg",
	"temporaryFile" : cactiFolder+"temporary.cfg",
	"outFile" : cactiFolder+"outTemporary.txt"
}

def simulate_SRAM(SRAMSizeBase, SearchAreaWidth, CTUSize, findBestReadPorts=True):
	try:
		#assert(False) #Remove this assert to allow buffering results.
		with open("dictsPartial_"+str(SearchAreaWidth)+"_"+str(SRAMSizeBase)+".raw", "rb") as fwDf:
			dfMemories = pickle.load(fwDf)
	except:
		#Parameters
		bandwidths = [16, 8, 4]

		bankCounts = [2 ** j for j in range(0, 8)]

		blockSizes = [1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128, 192, 256, 320, 384, 448, 512, 576, 640, 704, 768, 832, 896, 960, 1024]
		
		#Simulate organizations
		dfMemories = pd.DataFrame(sCacti.simulateOrganizations(cactiParameters, SRAMSizeBase, SearchAreaWidth, bandwidths, bankCounts, blockSizes, CTUSize, findBestReadPorts))

		with open("dictsPartial_"+str(SearchAreaWidth)+"_"+str(SRAMSizeBase)+".raw", "wb") as fwDf:
			pickle.dump(dfMemories, fwDf)
	
	return dfMemories
	
def generateReadPower(df, CTUSize, CTUAmount, TZSCandidates):
	#Total number of samples that should be requested for each CTU
	samplesRequestedPerCTU = TZSCandidates * CTUSize * CTUSize

	#Number of clock cycles requesting data from the memory, for each CTU
	cyclesRequestingDataPerCTU = samplesRequestedPerCTU / (CTUSize * df["band"])

	#Energy consumed requesting data for each CTU
	#Considers that at each clock cycle, all ports from all banks are activated,
	njPerCTU = (cyclesRequestingDataPerCTU * df["readPorts"] * df["bankCount"] * df["readEnergy (nJ)"])
	
	#Power dissipated for the processing of all CTUs processed in one second
	readWatts = (CTUAmount * njPerCTU) / 1000000000
	
	#Fill dataframe with results
	#df["energyPerCTU (nJ)"] = njPerCTU
	df["readPower (W)"] = readWatts

def generateWritePower(df, CTUSize, frameWidth, frameHeight, fps):
	#Total number of memory blocks written according to frame width
	widthBlocks = (frameWidth / df["blockSize (B)"]).apply(np.ceil)

	#Total number of memory blocks written according to frame height
	heightBlocks = 3 * frameHeight - 2 * CTUSize
	
	#Total number of memory blocks written per second
	writeCount = widthBlocks * heightBlocks * fps
	
	#Write Power
	df["writePower (W)"] = writeCount * df["readEnergy (nJ)"] / 1000000000

def generateWritePowerCB(df, CTUSize, frameWidth, frameHeight, fps):
	#Total number of memory blocks written according to frame width
	widthBlocks = (frameWidth / df["blockSize (B)"]).apply(np.ceil)
	
	#Total number of memory blocks written according to frame height
	heightBlocks = math.ceil(frameHeight/CTUSize) * CTUSize

	#Total number of memory blocks written per second
	writeCount = widthBlocks * heightBlocks * fps
	
	#Write Power
	df["writePower (W)"] = writeCount * df["readEnergy (nJ)"] / 1000000000
  
def main():
	##################################
	##################################
	# PARAMETERS

	#CTU Size
	CTUSize = 64

	#Width of the Search Area
	# CTUSize + 2*SearchRange
	SearchAreaWidth = 192
	
	#SRAM Size
	#Number of samples inside SRAM
	# (SearchAreaWidth * SearchAreaHeight) ~= (SearchAreaWidth * SearchAreaWidth)
	SRAMSizeBase = SearchAreaWidth*SearchAreaWidth
	
	#Number of blocks processed by TZS algorithm
	TZSCandidates = 326

	#Target throughput
	frameWidth = 3840
	frameHeight = 2160
	fps = 120

	#Number of CTUs to be processed per second
	CTUAmount = math.ceil(frameWidth/CTUSize) * math.ceil(frameHeight/CTUSize) * fps

	##################################
	##################################
	# Processing Unit Results
	df_ProcessingUnit = [
		{"band":4, "Resolution":"4K", "fps": 60, "Power ProcessingUnit (W)": 84.98/1000},
		{"band":8, "Resolution":"4K", "fps": 60, "Power ProcessingUnit (W)": 70.83/1000},
		{"band":4, "Resolution":"4K", "fps":120, "Power ProcessingUnit (W)":122.74/1000},
		{"band":8, "Resolution":"4K", "fps":120, "Power ProcessingUnit (W)":106.87/1000}
	]
	df_ProcessingUnit = pd.DataFrame(df_ProcessingUnit)
	print("Table II:")
	print(df_ProcessingUnit)
	df_ProcessingUnit = df_ProcessingUnit.loc[df_ProcessingUnit["fps"] == fps]
	print(df_ProcessingUnit)
	
	##################################
	##################################
	# Simulate SRAM Memories With Cacti

	df_SRAM_SA = simulate_SRAM(SRAMSizeBase, SearchAreaWidth, CTUSize, True)
	df_SRAM_CB = simulate_SRAM(CTUSize*CTUSize, CTUSize, CTUSize, False)

	#df_SRAM_SA.dropna(inplace=True)
	df_SRAM_SA = df_SRAM_SA[df_SRAM_SA.results == "ok"]
	df_SRAM_CB = df_SRAM_CB[df_SRAM_CB.results == "ok"]
	df_SRAM_SA.drop(columns=["results"], inplace=True)
	df_SRAM_CB.drop(columns=["results"], inplace=True)

	##################################
	##################################
	# Generage Read and Write Power

	generateReadPower(df_SRAM_SA, CTUSize, CTUAmount, TZSCandidates)
	generateWritePower(df_SRAM_SA, CTUSize, frameWidth, frameHeight, fps)
	generateReadPower(df_SRAM_CB, CTUSize, CTUAmount, TZSCandidates)
	generateWritePowerCB(df_SRAM_CB, CTUSize, frameWidth, frameHeight, fps)

	# 3D Graphs are generated with readPower results:
	#df_SRAM_SA["readPower (W)"]
	
	# Generate Total Power
	df_SRAM_SA["TotalPower (W)"] = (df_SRAM_SA["leakagePower (mW)"] )/1000 + df_SRAM_SA['readPower (W)'] + df_SRAM_SA['writePower (W)']
	df_SRAM_CB["TotalPower (W)"] = (df_SRAM_CB["leakagePower (mW)"] )/1000 + df_SRAM_CB['readPower (W)'] + df_SRAM_CB['writePower (W)']

	df_SRAM_SA.sort_values(by=['TotalPower (W)'], inplace=True)
	df_SRAM_CB.sort_values(by=['TotalPower (W)'], inplace=True)
	
	##################################
	##################################
	# Remove organizations which access time are higher than processing unit clock period
	df_SRAM_SA.drop(df_SRAM_SA[df_SRAM_SA["accessTime (ns)"] > 0.7587].index, inplace = True)
	df_SRAM_CB.drop(df_SRAM_CB[df_SRAM_CB["accessTime (ns)"] > 0.7587].index, inplace = True)

	# Remove band=16
	df_SRAM_SA.drop(df_SRAM_SA[df_SRAM_SA["band"] == 16].index, inplace = True)
	df_SRAM_CB.drop(df_SRAM_CB[df_SRAM_CB["band"] == 16].index, inplace = True)

	##################################
	##################################
	# Analyze results:

	print("\n\n\tMemory organizations for SA SRAM:\n")
	print("Best SA memories with band=8")
	print(df_SRAM_SA[df_SRAM_SA["band"] == 8].iloc[0:3])
	print("Best SA memories with band=4")
	print(df_SRAM_SA[df_SRAM_SA["band"] == 4].iloc[0:3])

	print("\n\n\tMemory organizations for CB SRAM:\n")
	print("Best CB memories with band=8")
	print(df_SRAM_CB[df_SRAM_CB["band"] == 8].iloc[0:3])
	print("Best CB memories with band=4")
	print(df_SRAM_CB[df_SRAM_CB["band"] == 4].iloc[0:3])


	# Get the organization from the minimal power of each band
	dfBestSA = df_SRAM_SA.loc[df_SRAM_SA.groupby("band")['TotalPower (W)'].idxmin()]
	dfBestSA = dfBestSA[["band", "TotalPower (W)"]]
	dfBestSA = dfBestSA.rename(columns={"TotalPower (W)": "Power SA (W)"})

	dfBestCB = df_SRAM_CB.loc[df_SRAM_CB.groupby("band")['TotalPower (W)'].idxmin()]
	dfBestCB = dfBestCB[["band", "TotalPower (W)"]]
	dfBestCB = dfBestCB.rename(columns={"TotalPower (W)": "Power CB (W)"})
	
	##################################
	##################################
	# Merge results from SA SRAM, CB SRAM, and Processing Unit:

	dfSystem = df_ProcessingUnit.merge(dfBestSA, on="band", how='outer')
	dfSystem = dfSystem.merge(dfBestCB, on="band", how='outer')
	dfSystem["TotalPower (W)"] = dfSystem["Power SA (W)"] + dfSystem["Power CB (W)"] + dfSystem["Power ProcessingUnit (W)"]

	print("\n\n\tFinal Results for the system:\n")
	print(dfSystem)


main()
