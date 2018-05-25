"""
Simple Waveform Transfer for Keysight AWGs
Author: Morgan Allison
Updated: 05/18
Creates a simple waveform, transfers it to the M8190A, and begin playback.
Python 3.6.4
PyVISA 1.9.0
NumPy 1.14.2
Tested on M8190A
"""

import numpy as np
import visa


def search_connect(ipAddress):
    """Configures and returns instrument VISA object using its IP address."""
    rm = visa.ResourceManager()
    inst = rm.open_resource('TCPIP0::{}::inst0:INST'.format(ipAddress))
    inst.timeout = 10000
    inst.write('*cls')
    print('Connected to {}'.format(inst.query('*idn?')))
    return inst


def create_wfm(fs, cf, rl, res='WPR'):
    """Creates and returns a waveform with the appropriate binary formatting
    based on the chosen DAC resolution and checks for minimum size and wfm
    granularity."""
    if res.lower() == 'wpr':
        if rl < 240:
            raise ValueError('Waveform must be at least 240 samples.')
        if rl % 48 != 0:
            raise ValueError('Waveform must have a granularity of 48.')
    elif res.lower() == 'wsp':
        if rl < 320:
            raise ValueError('Waveform must be at least 320 samples.')
        if rl % 64 != 0:
            raise ValueError('Waveform must have a granularity of 64.')
    else:
        raise ValueError('Invalid output resolution selected. Choose \'wpr\' for 14 bits or \'wsp\' or 12 bits.')

    t = np.linspace(0, rl / fs, rl)
    wfm = np.sin(2 * np.pi * cf * t)
    if res.lower() == 'wpr':
        wfm = np.array(8191 * wfm, dtype=np.int16) << 2
    elif res.lower() == 'wsp':
        wfm = np.array(2047 * wfm, dtype=np.int16) << 4
    return wfm


def err_check(inst):
    """Checks for and prints out all errors in error queue."""
    while inst.query('*esr?') != '0\n':
        print(inst.query('syst:err?'))
    print(inst.query('syst:err?'))


def main():
    awg = search_connect('141.121.210.216')
    awg.write('*rst')
    awg.query('*opc?')
    awg.write('abort')

    awg.write('func:mode arb')
    print('Output mode: {}'.format(awg.query('func:mode?').strip()))

    # Configure DC offset and signal amplitude.
    offset = 0
    amp = 1
    awg.write('dc:volt:offs {}'.format(offset))
    awg.write('dc:volt:ampl {}'.format(amp))
    ampRead = float(awg.query('dc:volt:ampl?').strip())
    offsetRead = float(awg.query('dc:volt:offs?').strip())
    print('Amplitude: {} V, Offset: {} V'.format(ampRead, offsetRead))

    # Define a waveform.
    res = 'wsp'     # use 'wsp' for 12-bit and 'wpr' for 14-bit
    fs = 8e9
    f = 100e6
    rl = fs / f * 64

    awg.write('trace:dwidth {}'.format(res))
    res = awg.query('trace:dwidth?').strip()
    print('Output res/mode: {}'.format(res))

    wfm = create_wfm(fs, f, rl, res=res)

    # Define segment 1 and populate it with waveform data.
    awg.write('trace:def 1, {}'.format(rl))
    awg.write_binary_values('trace:data 1, 0, ', wfm, datatype='h')

    # Configure and turn on output path.
    awg.write('output1:route dc')
    awg.write('output:norm on')
    print('Output path: {}'.format(awg.query('output1:route?')))

    # Assign segment 1 to trace (channel) 1 and start continuous playback.
    awg.write('trace:select 1')
    awg.write('init:cont on')
    awg.write('init:imm')
    awg.query('*opc?')

    err_check(awg)


if __name__ == '__main__':
    main()
