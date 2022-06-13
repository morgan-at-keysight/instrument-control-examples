# X-series Analyzer Option Checker
# Author: Morgan Allison
# Updated: 06/2022

import pyvisa

def main():
    """Establishes communication with X-series signal analyzer
    and prints out all installed options."""

    # This is a VISA resource manager object, use it to connect to your instrument
    rm = pyvisa.ResourceManager()
    # the string I used here was copied directly from Keysight Connection Expert
    xsa = rm.open_resource('TCPIP0::192.168.50.200::hislip0::INSTR')

    # Now I can interact with the spectrum analyzer object by calling
    # .write(), .query(), .read(), etc. methods

    # Reset the instrument and wait for reset operation to complete
    xsa.write('*RST')
    xsa.query('*OPC?')

    # get instrument identifier
    instID = xsa.query('*IDN?')
    # I'm using an f-string here, which uses {var} to insert variables into strings
    print(f'Connected to {instID}')

    # Query, save, and print out all the options installed on the analyzer
    optionString = xsa.query(":SYSTem:OPTions?")
    print(optionString)

if __name__ == '__main__':
    main()
