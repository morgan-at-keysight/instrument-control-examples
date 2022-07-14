# Author: Morgan Allison
# Updated: 07/22 
# 
# Sets up IQ analyzer mode, configures a trigger that will capture
# events with long time periods (much longer than the instrument's timeout),
# and saves trace data to csv files
# 
# Obligatory warning that this software has not gone through
# the standard Keysight software development process. It was
# written by a field application engineer as a one-off example.
# 
# Python 3.9.x
# PyVISA 1.12.x
# Matplotlib 3.4.x
# NumPy 1.22.x
# to get pyvisa, matplotlib, and numpy open windows command prompt and type:
# pip install pyvisa
# pip install matplotlib
# pip install numpy


import csv
import pyvisa
from datetime import datetime, timezone, timedelta
from time import sleep
import matplotlib.pyplot as plt
import numpy as np

def main():
    # Create an instrument object with pyvisa and set the timeout
    sa = pyvisa.ResourceManager().open_resource('TCPIP0::192.168.50.200::hislip0::INSTR')
    sa.timeout = 5000 # ms
    
    # Now the spectrum analyzer object can be controlled by calling
    # .write(), .query(), .read(), etc. methods

    # Reset the instrument and wait for reset operation to complete
    sa.write('*RST')
    sa.query('*OPC?')

    # get instrument identifier
    instID = sa.query('*IDN?')
    # I'm using an f-string here, which uses {var} syntax to insert variables into strings
    print(f'Connected to {instID}')

    # Measurement setup
    cf = 5e9
    rbw = 100
    refLevel = -50
    ifBw = 8e6
    xScale = 3e-3
    trigDelay = -100e-6
    trigLevel = -40 

    # Results setup
    # The timestamp and ".csv" will be appended to each saved file
    baseFileName = 'C:\\temp\\iqa_trace_'
    numRepetitions = 20
    
    # Set up a timezone-contextualized timestamp
    # PDT is permanently GMT-7 hr: YYYYMMdd_hh-mm-ss
    tz = timezone(offset=timedelta(hours=-7), name='pdt')

    # Set up IQ Analyzer mode for a complex spectrum measurement
    # The default shows both a spectrum trace and IQ vs time traces
    sa.write(f':INSTrument:SELect BASIC')
    sa.write(f':CONFigure:SPECtrum:NDEFault')
    
    # Set cf, rbw, if bandwidth (aka span), and turn off averaging
    # Note that the acquisition time in this mode is determined by resolution bandwidth. Low RBW --> long acq time
    sa.write(f':SENSe:FREQuency:CENTer {cf}')
    sa.write(f':SENSe:SPECtrum:BANDwidth:RESolution {rbw}')
    sa.write(f':SENSe:SPECtrum:BANDwidth:IF:SIZE {ifBw}')
    sa.write(f':SENSe:SPECtrum:AVERage:STATe off')

    # Set 
    sa.write(f':DISPlay:SPECtrum:VIEW:WINDow2:TRACe:X:SCALe:PDIVision {xScale}')
    sa.write(f':DISPlay:SPECtrum:VIEW:WINDow:TRACe:Y:SCALe:RLEVel {refLevel}')
    
    # Set RF burst trigger
    sa.write(f':TRIGger:SEQuence:RFBurst:LEVel:TYPE ABSolute')
    sa.write(f':TRIGger:SEQuence:RFBurst:LEVel:ABSolute {trigLevel}')
    sa.write(f':TRIGger:SEQuence:RFBurst:DELay {trigDelay}')
    sa.write(f':TRIGger:SEQuence:RFBurst:DELay:STATe on')
    sa.write(f':SENSe:SPECtrum:TRIGger:SOURce RFBurst')

    # Make sure binary formatting for trace data is correct (data type and endianness)
    sa.write(':FORMat:TRACe:DATA REAL,32')
    sa.write(':FORMat:BORDer SWAPped')

    sa.write(':INITiate:CONTinuous 0')
    
    for i in range(numRepetitions):
        # Single shot, start acquisition
        sa.write(':INITiate:SPECtrum')

        
        # Poll the status:operation register to see if the instrument is waiting for trigger
        triggered = 0
        while triggered == 0:
            triggered = int(sa.query('status:operation:condition?')) & (1 << 5)
            sleep(0.01)
            # print(f'triggered? {triggered}')

        # Once the instrument receives a trigger
        # Get current time
        rawTimestamp = datetime.now(tz)
        # Convert datetime object to formatted string
        timestamp = rawTimestamp.strftime('%Y%m%d_%H-%M-%S')

        # After the instrument is triggered, it still needs to complete an acquisition,
        # so poll the "sweeping" bit until it turns off, then get trace data
        sweeping = 1
        while sweeping:
            sweeping = int(sa.query('status:operation:condition?')) & (1 << 3)
            sleep(0.01)
            # print(f'sweeping? {sweeping}')

        # Wait for acquisition to complete after receiving the trigger
        # This in addition to polling the "sweeping" bit is belt + suspenders
        sa.query('*opc?')

        # Grab trace data (expecting 32-bit big endian floating point data)
        envelope = sa.query_binary_values(f':FETCH:spectrum2?', datatype='f')
        spectrum = sa.query_binary_values(f':FETCH:spectrum4?', datatype='f')
        
        # the "meta" variable contains metadata about the measurement that we will use
        # to build time and frequency arrays for plotting/saving results
        # Page 425 in https://www.keysight.com/zz/en/assets/9018-02190/user-manuals/9018-02190.pdf?success=true
        meta = sa.query_binary_values(f':FETCH:spectrum1?', datatype='f')
        
        # Build frequency array from metadata
        fftPoints = int(meta[2])
        startFreq = meta[3]
        freqSpacing = meta[4]

        stopFreq = startFreq + (freqSpacing * fftPoints)
        freq = np.linspace(startFreq, stopFreq, fftPoints)

        # Build time array from metadata
        timePoints = int(meta[5])
        startTime = meta[6]
        timeSpacing = meta[7]
        stopTime = startTime + (timeSpacing * timePoints)

        timeArray = np.linspace(startTime, stopTime, timePoints)

        # # Print stuff
        # print(f'fft points: {fftPoints}')
        # print(f'first fft point: {startFreq}')
        # print(f'fft point spacing: {freqSpacing}')

        # # Plot stuff
        # plt.subplot(2,1,1)
        # plt.plot(timeArray, envelope)
        # plt.subplot(2,1,2)
        # plt.plot(freq, spectrum)
        # plt.show()

        # Save trace data to csv file
        fullFileName = f'{baseFileName}{timestamp}.csv'
        print(f'Saved data at {fullFileName}')
        with open(fullFileName, 'w', newline='\n') as f:
            writer = csv.writer(f, dialect='excel', delimiter=',', )
            writer.writerow(['Frequency (Hz)', 'Spectrum (dBm)', 'Time (sec)', 'Envelope (dBm)'])
            for f, s, t, e in zip(freq, spectrum, timeArray, envelope):
                writer.writerow([f, s, t, e])


if __name__ == '__main__':
    main()
