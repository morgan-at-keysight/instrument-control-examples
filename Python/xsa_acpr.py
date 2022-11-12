# X-series Analyzer ACPR Example
# Author: Morgan Allison
# Updated: 11/2022

import pyvisa

def main():
    """Establishes communication with X-series signal analyzer,
    sets up an ACPR measurement, takes a measurement, and prints results."""

    # User-configured variables
    acpMethod = 'ibw' # ibw, ibwrange, rbw
    avgNumber = 5

    # Main channel
    mainChCf = 6e9
    mainChBw = 100e6

    # Adjacent channel
    adjChEnable = 1 # 1=On, 0=Off
    adjChOffset = 100e6
    adjChBw = 100e6

    # Alternate channel
    altChEnable = 1 # 1=On, 0=Off
    altChOffset = 200e6
    altChBw = 100e6    

    # This is a VISA resource manager object, use it to connect to your instrument
    rm = pyvisa.ResourceManager()
    # the string I used here was copied directly from Keysight Connection Expert
    xsa = rm.open_resource('TCPIP0::192.168.4.59::hislip0::INSTR')
    xsa.timeout = 10000

    # Now I can interact with the spectrum analyzer object by calling
    # .write(), .query(), .read(), etc. methods

    # Reset the instrument and wait for reset operation to complete
    xsa.write('*RST')
    xsa.query('*OPC?')

    # get instrument identifier
    instID = xsa.query('*IDN?')
    # I'm using an f-string here, which uses {var} to insert variables into strings
    print(f'Connected to {instID}')

    # Select ACPR measurement
    xsa.write('configure:acpower')
    xsa.write('configure:acpower:ndefault')
    
    # Configure basic ACPR parameters
    xsa.write(f'acpower:method {acpMethod}')
    xsa.write(f'acpower:average:count {avgNumber}')
  
    # Configure main channel parameters
    xsa.write(f'sense:frequency:center {mainChCf}')
    xsa.write(f'acpower:carrier:list:bandwidth:integration {mainChBw}')

    # Configure offset definitions (center-to-center)
    xsa.write('acpower:offset:outer:type ctocenter')

    # Enable and configure adjacent and/or alternate channels
    xsa.write(f'acpower:offset:list:state {adjChEnable},{altChEnable}')
    xsa.write(f'acpower:offset:outer:list:frequency {adjChOffset}, {altChOffset}')
    xsa.write(f'acpower:offset:outer:list:bandwidth:integration {adjChBw}, {altChBw}')

    # Make a single-shot measurement
    xsa.write('initiate:continuous off')
    xsa.write('initiate:immediate')
    xsa.query('*opc?')

    # Get and print results, which are returned as a string of comma separated values
    results = xsa.query('fetch:acpower1?')
    results = results.split(',')
    
    carrierPwrdBm = float(results[1])
    referencePwrdBm = float(results[3])
    lowerOffsetARelPwrdBm = float(results[4])
    lowerOffsetAAbsPwrdBm = float(results[5])
    upperOffsetARelPwrdBm = float(results[6])
    upperOffsetAAbsPwrdBm = float(results[7])
    lowerOffsetBRelPwrdBm = float(results[8])
    lowerOffsetBAbsPwrdBm = float(results[9])
    upperOffsetBRelPwrdBm = float(results[10])
    upperOffsetBAbsPwrdBm = float(results[11])
    
    print(f'Carrier Power/Reference Power: {carrierPwrdBm:.4f} dBm/{referencePwrdBm:.4f} dBm')
    print()
    print(f'Adjacent channel absolute power: Lower = {lowerOffsetAAbsPwrdBm:.2f} dBm, Upper = {upperOffsetAAbsPwrdBm:.2f} dBm')
    print(f'Adjacent channel relative power: Lower = {lowerOffsetARelPwrdBm:.2f} dB, Upper = {upperOffsetARelPwrdBm:.2f} dB')
    print()
    print(f'Alternate channel absolute power: Lower = {lowerOffsetBAbsPwrdBm:.2f} dBm, Upper = {upperOffsetBAbsPwrdBm:.2f} dBm')
    print(f'Alternate channel relative power: Lower = {lowerOffsetBRelPwrdBm:.2f} dB, Upper = {upperOffsetBRelPwrdBm:.2f} dB')

if __name__ == '__main__':
    main()
