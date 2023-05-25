# Example code written by Morgan Allison
# Obligatory warning that this software has not gone through
# the standard Keysight software development process. It was
# written by a field application engineer as a one-off example.

# to get pyvisa, open windows command prompt and type:
# pip install pyvisa


import pyvisa

def main():

    # Establish communication with instrument VISA object
    visaAddress = "TCPIP0::192.168.4.83::hislip0::INSTR"
    instrument = pyvisa.ResourceManager().open_resource(visaAddress)
    instrument.timeout = 10000
    
    print(f'Connected to {instrument.query("*idn?")}')
    
    # Preset instrument
    instrument.write(f'*rst')
    instrument.query(f'*opc?')

    # Source variables
    sourceCf = 4e9 # Hz
    sourceSampleRate = 1e9 # samples/sec
    sourceAmp = -10 # dBm
    wfmFile = "C:\\Temp\\waveforms\\qpsk-waveform.csv"

    # Trigger variables
    sourceInternalTrigger = 'PARB' # S1Marker | S2Marker | S3Marker | S4Marker | OFF
    useInternalTrig = True
    sourcePxiTrigger = 'PARB' # S1Marker | S2Marker | S3Marker | S4Marker | OFF
    sourcePxiTriggerLine = 0 # 0-7

    # RRH variables
    rrhHeadNumber = 1 # 1 or 2
    rrhPortNumber = 1 # 1 or 2
    rrhPortArgument = f'RRH{rrhHeadNumber}RFHD{rrhPortNumber}'
    useRrh = True

    # RRH setup
    if useRrh:
        instrument.write(f':SENSe:FEED:RF:PORT:OUTPut {rrhPortArgument}')
    else:
        # Options are "RFOut" (normal RF Output port), "RFHD" (RF Half-Duplex Port) or "RFFD" (RF Full-Duplex Port) 
        instrument.write(f':SENSe:FEED:RF:PORT:OUTPut RFOut')

    # Source setup
    instrument.write(f':source:FREQuency {sourceCf}')
    instrument.write(f':SOURce:POWer:LEVel:IMMediate:AMPLitude {sourceAmp}')
    instrument.write(f':SOURce:RADio:ARB:SCLock:RATE {sourceSampleRate}')
    
    # Waveform setup
    instrument.write(f':SOURce:RADio:ARB:LOAD "{wfmFile}"')
    instrument.query("*OPC?")
    instrument.write(f':SOURce:RADio:ARB:WAVeform "{wfmFile}"')
    instrument.query("*OPC?")

    # Trigger setup
    if useInternalTrig:
        instrument.write(f':TRIGger[:SEQuence]:INTernal:SOURce:OUTPut {sourceInternalTrigger}')
    else:
        instrument.write(f':TRIGger:PXIE:SOURce:SEQuence:OUTPut {sourcePxiTrigger}')
        instrument.write(f':TRIGger:PXIE:SOURce:SEQuence:OUTPut:LINE {sourcePxiTriggerLine}')

    # Enable arb, modulation, and RF output
    instrument.write(f':SOURce:RADio:ARB:STATe 1')
    instrument.write(f':OUTPut:MODulation:STATe 1')
    instrument.write(f':OUTPut:STATe 1')

if __name__ == '__main__':
    main()
