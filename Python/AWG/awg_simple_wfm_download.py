"""
Simple Waveform Download for Keysight AWGs
Author: Morgan Allison
Updated: 06/18
Creates a simple waveform, transfers it to the M8190A, and begin playback.
Python 3.6.4
PyVISA 1.9.0
NumPy 1.14.2
Tested on M8190A
"""

import numpy as np
import visa


class awgError(Exception):
    """Generic class for AWG related errors"""
    pass


def search_connect(ipAddress):
    """Configures and returns instrument VISA object using its IP address."""
    rm = visa.ResourceManager()
    inst = rm.open_resource(f'TCPIP0::{ipAddress}::inst0:INST')
    inst.timeout = 10000
    inst.write('*cls')
    print('Connected to', inst.query('*idn?'))
    return inst


def err_check(inst):
    """Checks for and prints out all errors in error queue."""
    while inst.query('*esr?') != '0\n':
        print(inst.query('syst:err?'))
    print(inst.query('syst:err?'))


def check_wfm(wfm, res='wsp'):
    """Checks minimum size and granularity and returns waveform with
    appropriate binary formatting based on the chosen DAC resolution."""
    if res.lower() == 'wpr':
        gran = 48
        minLen = 240
        binMult = 8191
        binShift = 2
    elif res.lower() == 'wsp':
        gran = 64
        minLen = 320
        binMult = 2047
        binShift = 4
    else:
        raise awgError('Invalid output resolution selected. Choose \'wpr\' for 14 bits or \'wsp\' or 12 bits.')

    rl = len(wfm)
    if rl < minLen:
        raise awgError(f'Waveform must be at least {minLen} samples.')
    if rl % gran != 0:
        raise awgError(f'Waveform must have a granularity of {gran}.')

    return np.array(binMult * wfm, dtype=np.int16) << binShift


def main():
    """Simple waveform download example."""
    # Use hostname or IP address of instrument
    awg = search_connect('TW56330445.cla.is.keysight.com')
    awg.write('*rst')
    awg.query('*opc?')
    awg.write('abort')

    # User-defined sample rate and sine frequency
    ############################################################################
    fs = 10e9
    cf = 100e6
    ############################################################################

    # Configure AWG output mode
    awg.write('func:mode arb')
    print('Output mode:', awg.query('func:mode?').strip())

    # Define resolution
    # use 'wsp' for 12-bit and 'wpr' for 14-bit
    res = 'wsp'
    awg.write(f'trace1:dwidth {res}')
    print('Output res/mode:', awg.query('trace1:dwidth?').strip())

    # Set sample rate
    awg.write(f'frequency:raster {fs}')
    print('Sample rate: ', awg.query('frequency:raster?').strip())

    # Configure and enable DC output path.
    awg.write('output1:route dc')
    awg.write('output1:norm on')
    print('Output path:', awg.query('output1:route?').strip())

    # Configure DC offset and signal amplitude.
    offset = 0
    amp = 1
    awg.write(f'dc:volt:ampl {amp}')
    ampRead = float(awg.query('dc:volt:ampl?').strip())
    awg.write(f'dc:volt:offs {offset}')
    offsetRead = float(awg.query('dc:volt:offs?').strip())
    print(f'Amplitude: {ampRead} V, Offset: {offsetRead} V')

    # Define a waveform
    rl = fs / cf * 64
    t = np.arange(0, rl) / fs
    t = np.linspace(0, rl / fs, rl, endpoint=False)
    wfm = check_wfm(np.sin(2 * np.pi * cf * t), res)

    # Define segment 1 and populate it with waveform data.
    awg.write(f'trace:def 1, {rl}')
    awg.write_binary_values('trace:data 1, 0, ', wfm, datatype='h')

    # Assign segment 1 to trace (channel) 1 and start continuous playback.
    awg.write('trace:select 1')
    awg.write('init:cont on')
    awg.write('init:imm')
    awg.query('*opc?')

    err_check(awg)
    awg.close()


if __name__ == '__main__':
    main()
