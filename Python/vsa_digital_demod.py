"""
VSA Digital Demod Example
Author: Morgan Allison
Updated: 06/18
Sets up a digital demodulation measurement in VSA running on an X-Series
analyzer and acquires measurement information.
Uses socket_instrument.py for instrument communication.
Python 3.6.4
NumPy 1.14.2
Tested on N9030B PXA
"""

import socketscpi
import matplotlib.pyplot as plt

def main():
    """Sets up a digital demodulation measurement in VSA running on an X-Series
    analyzer and acquires an EVMrms measurement on a digital signal."""

    # User-definable configurations variables
    cf = 1e9
    span = 10e6
    numSymbols = 1024
    modType = 'qpsk'
    sRate = 1e6
    filterShape = 'rootraisedcosine'
    alpha = 0.5

    # Connect to and reset VSA.
    vsa = socketscpi.SocketInstrument('127.0.0.1', port=5026)
    print('Connected to:', vsa.instId)
    vsa.write('*rst')

    # Configure measurement, frequency/span, and perform a vertical autorange.
    vsa.write('measure:nselect 1')
    vsa.write('measure:configure ddemod')
    vsa.write(f'sense:frequency:center {cf}')
    vsa.write(f'sense:frequency:span {span}')
    vsa.write('input:analog:range:auto')
    vsa.query('*opc?')

    # Configure digital demod parameters
    vsa.write(f'ddemod:format:rlength {numSymbols}')
    vsa.write(f'ddemod:mod "{modType}"')
    vsa.write(f'ddemod:srate {sRate}')
    vsa.write(f'ddemod:filter "{filterShape}"')
    vsa.write(f'ddemod:filter:abt {alpha}')

    # Set up and execute a single-shot acquisition and measurement.
    vsa.write('initiate:continuous off')
    vsa.write('initiate:immediate')
    vsa.query('*opc?')

    """By default, the digital demod result table is placed in trace 4.
    Get a list of potential measurements for ALL modulation types. Only a subset
    of these will be populated for any given modlation type, and the rest will
    return '***'."""
    measList = vsa.query('trace4:data:table:name?').strip().split(',')
    # Query each measurement and print out the measurement name and corresponding value.
    for name in measList:
        meas = vsa.query(f'trace4:data:table? {name}').strip()
        print(f'{name}: {meas}')

    vsa.write('format:trace:data real64')
    evmVsTime = vsa.binblockread('trace3:data:y?', datatype='d').byteswap()

    vsa.write('format:trace:data real64')
    i = vsa.binblockread('trace1:data:x?', datatype='d').byteswap()
    q = vsa.binblockread('trace1:data:y?', datatype='d').byteswap()

    plt.plot(evmVsTime)
    plt.show()
    # Check for errors and gracefully disconnect.
    vsa.err_check()
    vsa.disconnect()


if __name__ == '__main__':
    main()
