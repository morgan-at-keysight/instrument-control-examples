import pyvisa
rm = pyvisa.ResourceManager()

visaAddress = 'TCPIP0::141.121.37.90::hislip0::INSTR'

xsa = rm.open_resource(visaAddress)
xsa.timeout = 10000 # ms

stateFile = r"D:\Users\Instrument\Documents\SA\state\spur_test.state"
screenFile = r"D:\Users\Instrument\Documents\SA\screen\spurious_results.png"

xsa.write(f':INST:CONF:SA:SANalyzer')
xsa.query(f'*OPC?')
xsa.write(f'MMEMory:LOAD:STATe "{stateFile}"')
xsa.write(f':CONF:SPURious:NDEF')
xsa.query(f'*OPC?')
xsa.write(f':INITiate:CONTinuous 0')
xsa.write(f':INITiate:RESTart')
xsa.write(f':MMEMory:STORe:SCReen "{screenFile}"')
xsa.query(f'*OPC?')


"""Get and parse spurious results"""
# Get spurious results
# See documentation here: https://helpfiles.keysight.com/csg/SAMode/FlexUI.htm#meas_spur/Spurious%20Emissions%20Measurement.htm?TocPath=Spectrum%2520Analyzer%2520Mode%257CSpurious%2520Emissions%2520Measurement%257C_____0
rawResults = xsa.query(f':READ:SPURious?')

# Parse the results
results = [float(r) for r in rawResults.split(',')]
# The first value is the number of spurs
numSpurs = int(results[0])
print(numSpurs)

# The rest of the list is the spur data that we need to parse
rawSpurData = results[1::]

spurData = []

# There are 6 values per spur in the table
# Spur number, spur range, spur frequency, spur amplitude, spur amplitude limit, delta from limit to spur amplitude
# so we split the list into sub-lists of 6 values per spur
for i in range(numSpurs):
    startIndex = i * 6
    stopIndex = startIndex + 6
    spurData.append(rawSpurData[startIndex:stopIndex])

print(spurData)

"""Transfer the screenshot to remote PC"""
fileDestination = r"C:\Temp\spurious_results.png"
# Transfer data from file on instrument hard drive as a list of raw bytes
rawData = xsa.query_binary_values(f'mmemory:data? "{screenFile}"', datatype='c')
# Join the raw data into a single bytes object
data = b''.join(rawData)

# Write file to remote PC file location as bytes
with open(fileDestination, mode="wb") as f:
            f.write(data)