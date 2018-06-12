"""
Digital Upconverter Action Table Example for M8190
Author: Morgan Allison
Updated: 06/18
Creates a simple sine wave using digital upconversion in the M8190 and adjusts its amplitude,
phase, and frequency using the action table.
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


def config_segment_creator(fs, res):
    """Creates a configuration segment for use in the action table.
    Configuration segments slightly different from the normal data segments and are required to
    enable changes from the action table. These segments do not allow for looping, they must be
    at least 240 sample pairs in length, and the action occurs at the first sample marker
    after the 240th iq sample pair. Markers must also be ENABLED at the sequence index level
    for actions to occur.

    In the sequencer, the minimum waveform length is 257 * wfm granularity. This is to satisfy the
    minimum linear playtime requirement. This means that the minimum time between actions is
    257 * 24 / (FS/interpolation factor). So at maximum DAC sample rate and minimum interpolation
    factor, the minimum action period is 2.57 us. See page 125-126 in Keysight M8190A User's Guide
    (Edition 13.0, October 2017) for more information on linear playtime."""

    # Check interpolation factor and adjust sample rate accordingly.
    if 'intx' not in res.lower():
        raise awgError('Select a resolution compatible with digital up conversion ("intx<num>").')
    intFactor = int(res.lower().split('x')[-1])
    fs = fs / intFactor
    # Granularity in all interpolated modes is 24 samples.
    gran = 24

    # Create waveform (both i and q are all ones).
    rl = 257 * gran
    i = np.ones(rl)
    q = np.ones(rl)

    # Create a short marker pulse beginning at sample 240.
    sampMkr = np.zeros(rl, dtype=np.int16)
    syncMkr = np.zeros(rl, dtype=np.int16)
    sampMkr[240:480] = 1
    syncMkr[240:480] = 1

    # Apply appropriate binary formatting to waveforms and add markers.
    i = check_wfm(i, res)
    i += sampMkr
    q = check_wfm(q, res)
    q += syncMkr

    # Interleave i and q into a single waveform.
    segment = np.empty(2 * rl, dtype=np.int16)
    segment[0::2] = i
    segment[1::2] = q

    return segment


def action_table_builder(awg):
    """Builds an example action table that exercises all the capabilities of the DUC.

    Order of operations is to define a new action table index and then append a specific command
    to that index. See pages 307-309 in Keysight M8190A User's Guide (Edition 13.0, October 2017)
    for more information."""

    awg.write('action1:delete:all')
    awg.query('action1:define:new?')
    awg.write('action1:append 1, amplitude, 0.25')
    awg.query('action1:define:new?')
    awg.write('action1:append 2, amplitude, 1.0')
    awg.query('action1:define:new?')
    awg.write('action1:append 3, poffset, -0.25')
    awg.query('action1:define:new?')
    awg.write('action1:append 4, cfrequency, 100e6')
    awg.query('action1:define:new?')
    awg.write('action1:append 5, cfrequency, 1e6')
    awg.query('action1:define:new?')
    awg.write('action1:append 6, preset, 0.25')
    awg.query('action1:define:new?')
    awg.write('action1:append 7, srate, 2e6')
    awg.query('action1:define:new?')
    awg.write('action1:append 8, srun')
    awg.query('action1:define:new?')
    awg.write('action1:append 9, srestart')
    awg.query('action1:define:new?')
    awg.write('action1:append 10, shold')


def sequence_builder(awg, seqLength):
    """Creates a sequence that loads the same waveform several times and adjusts its
    characteristics using the action table.

    Command Documentation
    Load sequence index with configuration segment:
    stable:data <seq_table_index>, <control_entry>, <seq_loop_cnt>, <command_code>, <seg_id>, <seg_start>, <seg_end>
    Arguments for stable:data are six 32-bit registers that each control a certain aspect of the
    sequence. Individual bits should be "ORed" together if multiple bits are selected in a single
    <control_entry> parameter. Detailed descriptions of the command arguments (<control_entry>,
    <command_code>, etc.) can be found on pages 262-265 in Keysight M8190A User's Guide
    (Edition 13.0, October 2017)."""

    if not isinstance(seqLength, int):
        raise awgError('Sequence length must be an integer.')
    if seqLength < 2 or seqLength > 512e3:
        raise awgError('Sequence length must be between 2 and 512k.')
    awg.query(f'seq1:def:new? {seqLength}')

    # <control_entry> bit 31: read command code, bit 28: start of seq, bit 24: mkr enable.
    cmd = 1 << 31
    start = 1 << 28
    end = 1 << 30
    mkr = 1 << 24
    # <command_code> bits 31-16: action table id, bits 15-0: idle/config select.

    for i in range(seqLength):
        # If start of sequence, set start flag in addition to command code and marker enable.
        if i == 0:
            awg.write(f'stable1:data {i}, {cmd | start | mkr}, 1, {(i + 1) << 16 | 1 << 0}, 1, 0, #hffffffff')
        # If middle of sequence, set command code and marker enable.
        elif i < seqLength - 1:
            awg.write(f'stable1:data {i}, {cmd | mkr}, 1, {(i + 1) << 16 | 1 << 0}, 1, 0, #hffffffff')
        # If end of sequence, set end flag in addition to command code and marker enable.
        else:
            awg.write(f'stable1:data {i}, {cmd | mkr | end}, 1, {(i + 1) << 16 | 1 << 0}, 1, 0, #hffffffff')


def main():
    """Creates a simple sine wave using digital upconversion in the M8190."""
    awg = SocketInstrument('10.112.181.78', port=5025)
    print('Connected to:', awg.instId)
    awg.write('*rst')
    awg.query('*opc?')
    awg.write('abort')

    # User-defined sample rate, carrier frequency, and interpolation factor.
    ############################################################################
    fs = 7.2e9
    cf = 100e6

    # Define resolution
    # Use 'intx3', 'intx12', 'intx24', or 'intx48' to enable digital up conversion mode.
    res = 'intx3'
    ############################################################################

    awg.write(f'trace1:dwidth {res}')
    awg.write(f'trace2:dwidth {res}')
    res = awg.query('trace1:dwidth?').strip()
    print(f'Output res/mode: {res}')

    # Configure DUC carrier frequency.
    awg.write(f'carrier1:freq {cf}')
    print('DUC Carrier Frequency, Offset:', awg.query('carrier1:freq?'.strip()))

    # Set sample rate.
    awg.write(f'frequency:raster {fs}')
    print('Sample rate: ', awg.query('frequency:raster?'))

    # Set external reference.
    awg.write('roscillator:source ext')
    awg.write('roscillator:frequency 10e6')
    print('Reference source: ', awg.query('roscillator:source?').strip())
    print('Reference frequency: ', awg.query('roscillator:frequency?').strip())

    # Configure and enable DAC output path.
    awg.write('output1:route dac')
    awg.write('output1:norm on')

    # Create config segment and download to M8190.
    segment = config_segment_creator(fs, res)
    # Note the divide by two here, waveform length is defined in terms of IQ PAIRS.
    awg.write(f'trace1:def 1, {len(segment) / 2}')
    awg.binblockwrite('trace1:data 1, 0, ', segment)

    # Build action table and sequence.
    action_table_builder(awg)
    sequence_builder(awg, seqLength=10)

    # Configure AWG output mode.
    awg.write('func:mode stsequence')
    print('Output mode:', awg.query('func:mode?').strip())

    # Assign segment 1 to trace (channel) 1 and start continuous playback.
    awg.write('stable:seq:sel 0')
    awg.write('init:imm')
    awg.query('*opc?')

    # Check for errors and gracefully disconnect.
    awg.err_check()
    awg.disconnect()


if __name__ == '__main__':
    main()
