# Author: Morgan Allison
# Updated: 07/22 
# 
# Sets up zero span in swept analyzer mode, configures a trigger that will capture
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
# to get pyvisa and matplotlib, open windows command prompt and type:
# pip install pyvisa
# pip install matplotlib


import csv
import pyvisa
from datetime import datetime, timezone, timedelta
from time import sleep
import matplotlib.pyplot as plt

def main():
    """Establishes communication with X-series signal analyzer,
    configures basic settings, acquires a trace, and saves data to csv."""

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
    cf = 1.61625e9
    rbw = 3e6
    sweepTime = 5 # sec
    atten = 20

    trigDelay = -100e-3
    trigLevel = -20 

    # Results setup
    # The timestamp and ".csv" will be appended to each saved file
    baseFileName = 'C:\\temp\\zero_span_trace_'
    numRepetitions = 20

    # Set up a timezone-contextualized timestamp
    # PDT is permanently GMT-7 hr: YYYYMMdd_hh-mm-ss
    tz = timezone(offset=timedelta(hours=-7), name='pdt')

    # Set up IQ Analyzer mode for a complex spectrum measurement
    # The default shows both a spectrum trace and IQ vs time traces
    sa.write(f':INSTrument:SELect SA')
    sa.write(f':CONFigure:SANalyzer:NDEFault')
    
    # Set cf, rbw, sweep time, and attenuation
    sa.write(f':SENSe:FREQuency:CENTer {cf}')
    sa.write(f':SENSe:FREQuency:SPAN 0')
    sa.write(f':SENSe:BANDwidth:RESolution {rbw}')
    sa.write(f':SENSe:SWEep:TIME {sweepTime}')
    sa.write(f':SENSe:POWer:RF:ATTenuation {atten}')

    # Set RF burst trigger
    sa.write(f':TRIGger:SEQuence:SOURce RFBurst')
    sa.write(f':TRIGger:SEQuence:RFBurst:LEVel:TYPE ABSolute')
    sa.write(f':TRIGger:SEQuence:RFBurst:LEVel:ABSolute {trigLevel}')
    sa.write(f':TRIGger:SEQuence:RFBurst:DELay {trigDelay}')
    sa.write(f':TRIGger:SEQuence:RFBurst:DELay:STATe on')

    # Make sure binary formatting for trace data is correct (data type and endianness)
    sa.write(':FORMat:TRACe:DATA REAL,32')
    sa.write(':FORMat:BORDer SWAPped')

    sa.write(':INITiate:CONTinuous 0')
    
    for i in range(numRepetitions):
        # Single shot, start acquisition
        sa.write(':INITiate:SANalyzer')
        
        # Poll the status:operation register to see if the instrument is waiting for trigger
        # This bit will be HIGH while the instrument is waiting for a trigger
        # It will go LOW when it receives a trigger AND when it is idle/not making a measurement
        
        # There is a delay between when the INITiate:SANalyzer command is sent and when the bit goes high
        # So we add a delay in the code so that it doesn't immediately kick out of the while loop
        sleep(1)
        waitingForTrigger = 32
        while waitingForTrigger != 0:
            waitingForTrigger = int(sa.query('status:operation:condition?')) & (1 << 5)
            sleep(0.01)
            # print(f'waiting for trigger? {waitingForTrigger}')

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
            print(f'sweeping? {sweeping}')

        # Wait for acquisition to complete after receiving the trigger
        # This in addition to polling the "sweeping" bit is belt + suspenders
        sa.query('*opc?')

        # Grab raw trace data (expecting 32-bit big endian floating point data)
        raw = sa.query_binary_values(f':FETCH:SANalyzer1?', datatype='f')
        timeArray = raw[0::2]
        envelope = raw[1::2]

        # # Plot stuff
        # plt.plot(timeArray, envelope)
        # plt.show()

        # Save trace data to csv file
        fullFileName = f'{baseFileName}{timestamp}.csv'

        print(f'Saved data at {fullFileName}')

        with open(fullFileName, 'w', newline='\n') as f:
            writer = csv.writer(f, dialect='excel', delimiter=',', )
            writer.writerow(['Time (sec)', 'Envelope (dBm)'])
            for t, e in zip(timeArray, envelope):
                writer.writerow([t, e])


if __name__ == '__main__':
    main()
