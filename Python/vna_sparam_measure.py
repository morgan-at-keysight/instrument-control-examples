
"""
Simple VNA S Parameter Measurements
Author: Morgan Allison
Edited: 06/18
This script configures VNA to make a single sweep, acquiring all four 2-port
S parameters in separate traces and plots each in a separate subplot.
Uses socket_instrument.py for instrument communication.
Windows 7 64-bit
Python 3.6.4
Matplotlib 2.2.2
Tested on N5232B PNA-L
"""

from socket_instrument import *
import matplotlib.pyplot as plt


def vna_setup(vna, start=10e6, stop=26.5e9, numPoints=401, ifBw=1e3, dwell=1e-3, measName=['meas1'], measParam=['S11']):
    """Sets up basic S parameter measurement(s).

    Configures measurements and traces in a single window, sets start/stop
    frequency, number of points, IF bandwidth, and dwell time from preset state."""

    if not isinstance(measName, list) and not isinstance(measParam, list):
        raise TypeError('measName and measParam must be lists of strings, even when defining only one measurement.')

    vna.write('system:fpreset')
    vna.query('*opc?')
    vna.write('display:window1:state on')

    # Order of operations: 1-Define a measurement. 2-Feed measurement to a trace on a window.
    t = 1
    for m, p in zip(measName, measParam):
        vna.write(f'calculate1:parameter:define "{m}","{p}"')
        vna.write(f'display:window1:trace{t}:feed "{m}"')
        t += 1

    vna.write(f'sense1:frequency:start {start}')
    vna.write(f'sense1:frequency:stop {stop}')
    vna.write(f'sense1:sweep:points {numPoints}')
    vna.write(f'sense1:sweep:dwell {dwell}')
    vna.write(f'sense1:bandwidth {ifBw}')


def vna_acquire(vna, measName):
    """Acquires frequency and measurement data from selected measurement on VNA for plotting."""
    if not isinstance(measName, str):
        raise TypeError('measName must be a string.')

    # Select measurement to be transferred.
    vna.write(f'calculate1:parameter:select "{measName}"')

    # Format data for transfer.
    vna.write('format:border swap')
    vna.write('format real,64')  # Data type is double/float64, not int64.

    # Acquire measurement data.
    vna.write('calculate1:data? fdata')
    meas = vna.binblockread(dtype=np.float64)
    vna.query('*opc?')

    # Acquire frequency data.
    vna.write('calculate1:x?')
    freq = vna.binblockread(dtype=np.float64)
    vna.query('*opc?')

    return freq, meas


def main():
    """Configures VNA to make a single sweep, acquiring all four 2-port
    S parameters in separate traces and plots each in a separate subplot."""

    vna = SocketInstrument('10.112.181.177', port=5025)
    print('Connected to:', vna.instId)

    measName = ['meas1', 'meas2', 'meas3', 'meas4']
    measParam = ['S11', 'S21', 'S12', 'S22']
    plotColors = ['y', 'c', 'm', 'g']

    vna_setup(vna, stop=20e9, measName=measName, measParam=measParam)

    # Capture a single sweep and autoscale all traces in the window.
    vna.write('initiate:continuous off')
    vna.write('initiate:immediate')
    vna.query('*opc?')
    vna.write('display:window1:y:auto')

    # Acquire and plot data.
    fig = plt.figure(figsize=(15, 8))
    for t in range(len(measName)):
        freq, result = vna_acquire(vna, measName[t])
        ax = fig.add_subplot(2, 2, t + 1, facecolor='k')
        ax.plot(freq, result, c=plotColors[t])
        ax.set_title(f'Trace {t + 1}')
        ax.set_xlabel('Frequency (Hz)')
        ax.set_ylabel(f'{measParam[t]} (dB)')

    # Check for errors and gracefully disconnect.
    vna.err_check()
    vna.disconnect()

    # Clean up and display plots.
    plt.tight_layout()
    plt.show()


if __name__ == '__main__':
    main()
