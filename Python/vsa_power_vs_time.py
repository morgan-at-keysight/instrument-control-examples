"""
VSA Subset Acquisition Example
Author: Morgan Allison
Updated: 08/18
Sets up a logMagnitude vs time trace and an I vs Q trace, configures
time gate for the logMag trace and uses the gate to acquire subsets of
the acquisition time from the IQ trace.
Uses socket_instrument.py for instrument communication.
Python 3.6.4
NumPy 1.14.2
Tested on N9030B PXA
"""

import pyarbtools
import visa
import numpy as np
import matplotlib.pyplot as plt


def main():
    """Sets up a basic vector measurement in VSA, configures an IF
    magnitude trigger, acquires data, transfers the spectrum and Main
    Time traces, and plots them."""

    # User-definable configuration variables
    cf = 160e6
    span = 50e6
    dBmRange = 10
    numTones = 20
    toneSpacing = 2.5e6
    fStart = cf - (int(numTones / 2) * toneSpacing)
    print(f'fstart {fStart}, toneSpacing {toneSpacing}')
    # trigLevel = 50e-3
    # trigDelay = -1e-6
    # mainTime = 40e-6

    # Connect to and reset VSA.
    vsa = pyarbtools.communications.SocketInstrument('127.0.0.1', port=5025)
    print('Connected to:', vsa.instId)
    vsa.write('*rst')
    vsa.query('*opc?')

    # Configure measurement, frequency/span, and vertical range.
    vsa.write('measure:nselect 1')
    vsa.write('measure:configure vector')
    vsa.write(f'sense:frequency:center {cf}')
    vsa.write(f'sense:frequency:span {span}')
    vsa.write(f'input:analog:range:dbm {dBmRange}')
    vsa.write('trace1:format "GroupDelay"')

    # Set up and execute a single-shot acquisition and measurement.
    vsa.write('initiate:continuous on')
    vsa.write('initiate:immediate')
    vsa.query('*opc?')
    vsa.write('trace1:autoscale')
    vsa.write('trace1:y:scale:pdivision 2.5e-9')

    for n in range(numTones):
        vsa.write(f'trace1:marker{n + 1}:enable 1')
        vsa.write(f'trace1:marker{n + 1}:x {fStart + toneSpacing * n}')
        print(fStart + (toneSpacing * n))


    vsa.write('initiate:continuous off')
    numAvg = 10
    gdAverage = np.zeros(numTones)
    gdStdDev = np.zeros(numTones)
    gdPtP = np.zeros(numTones)
    gdRaw = np.zeros((numTones, numAvg))
    for yikes in range(5):
        for i in range(numAvg):
            vsa.write('initiate:immediate')
            vsa.query('*opc?')
            for n in range(numTones):
                gdRaw[n][i] = float(vsa.query(f'trace:marker{n + 1}:y?'))
        for n in range(numTones):
            gdAverage[n] = np.mean(gdRaw[n])
            gdStdDev[n] = np.std(gdRaw[n])
            gdPtP[n] = np.ptp(gdRaw[n])
        print('Measurement Standard Deviation')
        print(gdStdDev)
        print('Measurement Average')
        print(gdAverage)
        plt.plot(gdPtP)
    plt.show()


    # Check for errors and gracefully disconnect.
    vsa.err_check()
    vsa.disconnect()


if __name__ == '__main__':
    main()
