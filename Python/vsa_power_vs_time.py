"""
VSA Spectrum and Power vs Time Example
Author: Morgan Allison
Updated: 07/18
Sets up a basic vector measurement in VSA, configures an IF magnitude
trigger, acquires data, transfers the Spectrum and Main Time traces,
and plots them.
Uses socket_instrument.py for instrument communication.
Python 3.6.4
NumPy 1.14.2
Tested on N9030B PXA
"""

from socket_instrument import *
import matplotlib.pyplot as plt


def main():
    """Sets up a basic vector measurement in VSA, configures an IF
    magnitude trigger, acquires data, transfers the spectrum and Main
    Time traces, and plots them."""

    # User-definable configuration variables
    cf = 1e9
    span = 40e6
    vRange = 0
    trigLevel = 50e-3
    trigDelay = -1e-6
    mainTime = 40e-6

    # Connect to and reset VSA.
    vsa = SocketInstrument('127.0.0.1', port=5025)
    print('Connected to:', vsa.instId)
    vsa.write('*rst')

    # Configure measurement, frequency/span, and vertical range.
    vsa.write('measure:nselect 1')
    vsa.write('measure:configure vector')
    vsa.write(f'sense:frequency:center {cf}')
    vsa.write(f'sense:frequency:span {span}')
    vsa.write(f'input:analog:range:dbm {vRange}')

    # Configure trigger.
    vsa.write('input:trigger:style "MagnitudeLevel"')
    vsa.write(f'input:trigger:level {trigLevel}')
    vsa.write(f'input:trigger:delay {trigDelay}')

    # Configure acquisition time.
    # RBW points must be set to auto to explicitly set main time length.
    vsa.write('sense:rbw:points:auto 1')
    vsa.write(f'sense:time:length {mainTime}')

    # Set up and execute a single-shot acquisition and measurement.
    vsa.write('initiate:continuous off')
    vsa.write('initiate:immediate')
    vsa.query('*opc?')

    # Configure and prepare for data transfer.
    vsa.write('format:trace:data real64')  # This is float64/double, not int64
    traces = int(vsa.query('trace:count?').strip())
    fig, ax = plt.subplots(nrows=traces, figsize=(12, 9))

    # Loop through all traces, grab data/metadata, and plot
    for t in range(1, traces + 1):
        # vsa.query(f'trace{t}:data:valid?')
        name = vsa.query(f'trace{t}:data:name?').strip()
        xUnit = vsa.query(f'trace{t}:x:scale:unit?').strip()
        yUnit = vsa.query(f'trace{t}:y:scale:unit?').strip()

        # VSA uses big endian byte ordering on my computer, you may remove .byteswap() if needed
        vsa.write(f'trace{t}:data:x?')
        x = vsa.binblockread(dtype=np.float64).byteswap()
        vsa.write(f'trace{t}:data:y?')
        y = vsa.binblockread(dtype=np.float64).byteswap()
        ax[t - 1].plot(x, y)
        ax[t - 1].set_title(name)
        ax[t - 1].set_xlabel(xUnit)
        ax[t - 1].set_ylabel(yUnit)
    plt.tight_layout()
    plt.show()

    # Check for errors and gracefully disconnect.
    vsa.err_check()
    vsa.disconnect()


if __name__ == '__main__':
    main()
