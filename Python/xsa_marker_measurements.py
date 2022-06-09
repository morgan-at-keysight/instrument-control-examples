# Author: Morgan Allison
# Updated: 05/22
# Obligatory warning that this software has not gone through
# the standard Keysight software development process. It was
# written by a field solutions engineer as a one-off example.
# Python 3.9.x
# PyVISA 1.12.x
# NumPy 1.22.x
# To get pyvisa and NumPy open windows command prompt and type:
# pip install pyvisa
# pip install numpy

import pyvisa
import numpy as np

def main():
    """Establishes communication with X-series signal analyzer,
    configures basic settings, acquires a trace, and gathers
    measurements by stepping a marker across the span of interest."""

    # Measurement setup, not optimized for noise measurement right now
    cf = 2.4e9
    refLevel = 0
    span = 100e6
    rbw = 10e3
    markerBw = 20e6

    # This is a VISA resource manager object, use it to connect to your instrument
    rm = pyvisa.ResourceManager()
    # the string I used here was copied directly from Keysight Connection Expert
    xsa = rm.open_resource('TCPIP0::141.121.199.82::hislip0::INSTR')

    # Now I can interact with the spectrum analyzer object by calling
    # .write(), .query(), .read(), etc. methods

    # Reset the instrument and wait for reset operation to complete
    xsa.write('*RST')
    xsa.query('*OPC?')

    # get instrument identifier
    instID = xsa.query('*IDN?')
    # I'm using an f-string here, which uses {var} to insert variables into strings
    print(f'Connected to {instID}')

    # Set center frequency, span, rbw, and reference level
    xsa.write(f':SENSe:FREQuency:CENTer {cf}')
    xsa.write(f':SENSe:FREQuency:SPAN {span}')
    xsa.write(f':SENSe:BANDwidth:RESolution {rbw}')
    xsa.write(f':DISPlay:WINDow:TRACe:Y:SCALe:RLEVel {refLevel}')

    # Adjust timeout for long sweep
    originalTimeout = xsa.timeout
    xsa.timeout = 30

    # Single acquisition mode, start sweep, wait for operation to complete
    xsa.write(':INITiate:CONTinuous 0')
    xsa.write(':INITiate:IMMediate')
    xsa.query('*OPC?')

    # Adjust timeout back to normal
    xsa.timeout = originalTimeout

    # Configure marker
    # Start with all markers off
    xsa.write(':CALCulate:MARKer:AOFF')
    # Turn on marker 1
    xsa.write(':CALCulate:MARKer1:STATe 1')
    # (OPTIONAL) Set marker function to band density
    xsa.write(':CALCulate:MARKer1:FUNCtion BDENsity')
    # (OPTIONAL) Set marker bandwidth
    xsa.write(f':CALCulate:MARKer1:FUNCtion:BAND:SPAN {markerBw}')

    # Set up marker measurements
    numMeasurements = 20
    # Define marker measurement frequency list. Note that I am starting at the edge of the trace but taking
    # into account the marker bandwidth so I don't try to calculate band power outside of the trace
    mkrFreqList = np.linspace(cf - (span / 2) + (markerBw / 2), cf + (span / 2) - (markerBw / 2), numMeasurements)

    # Measure marker values sequentially at frequency points specified above
    mkrReadings = []
    for freq in mkrFreqList:
        # Set marker to a given frequency
        xsa.write(f':CALCulate:MARKer1:X {freq}')
        # Grab marker value
        mkrValue = float(xsa.query(':CALCulate:MARKer1:Y?'))
        # Append marker value to list in dBm/Hz
        mkrReadings.append(mkrValue)

    # Format binary data for saving to a text file.
    fileData = ''
    for f, m in zip(mkrFreqList, mkrReadings):
        fileData += f'{f}, {m}\n'
    # Write marker x and y values to a text file
    with open('C:\\temp\\mkr_results.txt', 'w+') as f:
        f.write(fileData)

if __name__ == '__main__':
    main()
