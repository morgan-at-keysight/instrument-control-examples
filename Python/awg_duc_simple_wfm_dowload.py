"""
Digital Upconverter Simple Waveform Download for M8190
Author: Morgan Allison
Updated: 06/18
Creates a simple sine wave using digital upconversion in the M8190.
Uses socket_instrument.py for instrument communication.
Python 3.6.4
NumPy 1.14.2
Tested on M8190A
"""

import numpy as np
from socket_instrument import *


class awgError(Exception):
    """Generic class for AWG related errors."""
    pass


def check_wfm(wfm, res='wsp'):
    """Checks minimum size and granularity and returns waveform with
    appropriate binary formatting based on the chosen DAC resolution.

    See pages 273-274 in Keysight M8190A User's Guide (Edition 13.0, October 2017) for more info."""

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
    elif 'intx' in res.lower():
        # Granularity, min length, and binary formatting are the same for all interpolated modes.
        gran = 24
        minLen = 120
        binMult = 16383
        binShift = 1
    else:
        raise awgError('Invalid output resolution selected.')

    rl = len(wfm)
    if rl < minLen:
        raise awgError(f'Waveform must be at least {minLen} samples.')
    if rl % gran != 0:
        raise awgError(f'Waveform must have a granularity of {gran}.')

    return np.array(binMult * wfm, dtype=np.int16) << binShift


def cw_iq_wfm_creator(fs, cf, res):
    """Creates baseband iq values that result in an unmodulated maximum amplitude sine wave."""
    # Check interpolation factor and adjust fs accordingly.
    if 'intx' not in res.lower():
        raise awgError('Select a resolution compatible with digital up conversion ("intx<num>").')
    intFactor = int(res.lower().split('x')[-1])
    fs = fs / intFactor

    # Create waveform (both i and q are all ones).
    rl = int(fs / cf * 24)
    i = np.ones(rl)
    q = np.ones(rl)

    # Create 50% duty cycle markers.
    sampMkr = np.append(np.ones(int(rl / 2), dtype=np.int16), np.zeros(int(rl / 2), dtype=np.int16))
    syncMkr = np.append(np.ones(int(rl / 2), dtype=np.int16), np.zeros(int(rl / 2), dtype=np.int16))

    # Apply appropriate binary formatting to waveforms and add markers.
    i = check_wfm(i, res)
    i += sampMkr
    q = check_wfm(q, res)
    q += syncMkr

    # Interleave i and q into a single waveform.
    iq = np.empty(2 * rl, dtype=np.int16)
    iq[0::2] = i
    iq[1::2] = q

    return iq


def main():
    """Creates a simple sine wave using digital upconversion in the M8190."""
    awg = SocketInstrument('10.112.181.78', port=5025)
    print('Connected to:', awg.instId)
    awg.write('*rst')
    awg.query('*opc?')
    awg.write('abort')

    # User-defined sample rate and sine frequency.
    ############################################################################
    fs = 7.2e9
    cf = 100e6
    ############################################################################

    # Define resolution
    # Use 'intx3', 'intx12', 'intx24', or 'intx48' to enable digital up conversion mode.
    res = 'intx3'
    awg.write(f'trace:dwidth {res}')
    res = awg.query('trace:dwidth?').strip()
    print(f'Output res/mode: {res}')

    # Configure DUC carrier frequency.
    awg.write('carrier1:freq 100e6')
    print('DUC Carrier Frequency, Offset:', awg.query('carrier1:freq?'.strip()))

    # Configure AWG output mode.
    awg.write('func:mode arb')
    print('Output mode:', awg.query('func:mode?').strip())

    # Set sample rate.
    awg.write(f'frequency:raster {fs}')
    print('Sample rate: ', awg.query('frequency:raster?'))

    # Configure and enable DAC output path.
    awg.write('output1:route dac')
    awg.write('output:norm on')

    # Define baseband iq waveform and download to segment 1.
    iq = cw_iq_wfm_creator(fs, cf, res)

    # Note the divide by two here, waveform length is defined in terms of iq pairs.
    awg.write(f'trace:def 1, {len(iq) / 2}')
    print(len(iq) / 2)
    awg.binblockwrite('trace1:data 1, 0, ', iq)

    # Assign segment 1 to trace (channel) 1 and start continuous playback.
    awg.write('trace1:select 1')
    awg.write('init:cont on')
    awg.write('init:imm')
    awg.query('*opc?')

    # Check for errors and gracefully disconnect.
    awg.err_check()
    awg.disconnect()


if __name__ == '__main__':
    main()
