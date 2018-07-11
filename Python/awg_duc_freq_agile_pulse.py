"""
Digital Upconverter Frequency Agile Pulse Train Example for M8190
Author: Morgan Allison
Updated: 06/18
Creates a pulsed cw signal with pulse shaping using digital upconversion in
the M8190 and adjusts pulse-to-pulse frequency using the action table.
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


def iq_wfm_combiner(i, q):
    """Combines i and q wfms into a single wfm for download to AWG."""
    iq = np.empty(2 * len(i), dtype=np.int16)
    iq[0::2] = i
    iq[1::2] = q
    return iq


def action_table_freq_builder(awg, freq):
    """Builds an example action table that changes carrier freq based on user-defined freq list.

    Order of operations is to define a new action table index and then append a specific command
    to that index. See pages 307-309 in Keysight M8190A User's Guide (Edition 13.0, October 2017)
    for more information."""

    if not isinstance(freq, list):
        raise awgError('freq must be a list.')

    awg.write('action1:delete:all')
    i = 1
    for f in freq:
        awg.query('action1:define:new?')
        awg.write(f'action1:append {i}, cfrequency, {f}')
        i += 1


def iq_pulse_envelope(fs, rise, fall, pw, shape='raised-cosine'):
    """Calculates and returns the iq envelope for a cw pulse."""

    validShapes = ['rectangular', 'trapezoidal', 'raised-cosine']
    if shape not in validShapes:
        raise awgError('Invalid pulse shape. Choose "rectangular", "raised-cosine", or "trapezoidal".')

    # Rise and fall times are 0-100% times. Pulse width is calculated at the 50% rise/fall points.
    rSamples = int(rise * fs)
    fSamples = int(fall * fs)
    pwSamples = int(pw * fs - rSamples / 2 - fSamples / 2)
    totalSamples = rSamples + pwSamples + fSamples

    # Create edge shapes.
    if shape == 'rectangular':
        rEdge = np.zeros(rSamples)
        fEdge = np.zeros(fSamples)
    elif shape == 'trapezoidal':
        rEdge = np.linspace(0, 1, rSamples)
        fEdge = np.linspace(1, 0, fSamples)
    else:  # raised-cosine
        rEdge = (1 + np.cos(np.linspace(-np.pi, 0, rSamples))) / 2
        fEdge = (1 + np.cos(np.linspace(0, np.pi, fSamples))) / 2
    # Create pulse on time.
    pulse = np.ones(pwSamples)

    # Concatenate edges with pulse on time and apply to i and q wfms.
    envelope = np.concatenate((rEdge, pulse, fEdge))
    i = envelope * np.ones(totalSamples)
    q = envelope * np.zeros(totalSamples)

    return i, q


def iq_pulse_calculator(fs, rise, fall, pw, shape, pri, res='intx3'):
    """Creates waveforms and idle samples required to build a pulse train that changes frequency.

    Configuration segments are required to enable changes from the action table. These segments do
    not allow for looping, they must be at least 240 sample pairs in length, and the action occurs
    at the first sample marker after the 240th iq sample pair. Markers must also be ENABLED at the
    sequence index level for actions to occur. To ensure that the action occurs at the correct time,
    the config waveform is defined to have 240 sample pairs and a marker is defined at the first
    sample of the pulse waveform.

    Returns: iqPulse, configWfm, idleSamples, endIdleSamples
    """

    if 'intx' not in res.lower():
        raise awgError('Select a resolution compatible with digital up conversion ("intx<num>").')
    intFactor = int(res.lower().split('x')[-1])
    if intFactor == 3:
        idleGran = 8
    elif intFactor == 12:
        idleGran = 2
    elif intFactor == 24 or intFactor == 48:
        idleGran = 1
    fs = fs / intFactor
    minLen = 120
    gran = 24

    # Create empty configuration segment.
    minConfigLen = 240
    iConfig = np.zeros(minConfigLen, dtype=np.int16)
    qConfig = np.zeros(minConfigLen, dtype=np.int16)
    configWfm = iq_wfm_combiner(iConfig, qConfig)

    # Create pulse on time wfm with markers.
    iPulse, qPulse = iq_pulse_envelope(fs, rise, fall, pw, shape)
    pwSamples = len(iPulse)

    # Minimum length check
    if pwSamples < minLen:
        extra = minLen - pwSamples
    # Granularity check
    else:
        extra = gran - (pwSamples % gran)

    # Create zero samples to pad the pulse waveform
    extraWfm = np.zeros(extra, dtype=np.int16)

    # Pad the pulse waveforms and add markers
    iPulse = check_wfm(np.append(iPulse, extraWfm), res)
    qPulse = check_wfm(np.append(qPulse, extraWfm), res)
    sampMkr = np.append(np.ones(int(len(iPulse) / 2), dtype=np.int16),
                        np.ones(int(len(iPulse) / 2), dtype=np.int16))
    iPulse += sampMkr
    qPulse += sampMkr
    iqPulse = iq_wfm_combiner(iPulse, qPulse)

    # Calculate idle samples (endIdleSamples is the last idle before the end of the sequence).
    idleSamples = int(fs * pri) - len(iqPulse) / 2 - len(configWfm) / 2
    endIdleSamples = idleSamples - len(configWfm) / 2
    rem1 = idleSamples % idleGran
    rem2 = endIdleSamples % idleGran
    if rem1 != 0:
        print(f'idleSamples granularity requirements not met, count increased by {rem1}.')
        idleSamples += rem
    if rem2 != 0:
        print(f'endIdleSamples granularity requirements not met, count increased by {rem2}.')
        endIdleSamples += rem

    return iqPulse, configWfm, idleSamples, endIdleSamples


def pulse_sequence_builder(awg, seqLength, idleSamples, endIdleSamples):
    """Creates a sequence of config and data waveforms that result in a simple pulse train whose
    frequency is changed from pulse to pulse using the action table.

    In order for the frequency to change before the pulse is generated, a(n empty) config waveform
    with an action table command needs to be played directly before the pulse waveform.

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
    awg.query(f'seq1:def:new? {3 * seqLength + 1}')

    # <control_entry> bit 31: read command code, bit 28: start of seq, bit 24: mkr enable.
    cmd = 1 << 31
    data = 0 << 31
    end = 1 << 30
    start = 1 << 28
    mkr = 1 << 24
    # <command_code> bits 31-16: action table id, bits 15-0: idle/config select.
    for i in range(seqLength):
        # If start of sequence, set start flag & command code and load configWfm.
        if i == 0:
            awg.write(f'stable1:data {3 *i}, {cmd | start}, 1, {(i + 1) <<16 | 1 << 0}, 1, 0, #hffffffff')
            awg.write(f'stable1:data {3 * i + 1}, {data | mkr}, 1, 1, 2, 0, #hffffffff')
            awg.write(f'stable:data {3 * i + 2}, {cmd}, 0, 0, 0, {idleSamples}, 0')
        # Middle of sequence, assign everything normally
        elif i < seqLength - 1:
            awg.write(f'stable1:data {3 *i}, {cmd}, 1, {(i + 1) <<16 | 1 << 0}, 1, 0, #hffffffff')
            awg.write(f'stable1:data {3 * i + 1}, {data | mkr}, 1, 1, 2, 0, #hffffffff')
            awg.write(f'stable:data {3 * i + 2}, {cmd}, 0, 0, 0, {idleSamples}, 0')
        # End of sequence, append configWfm to end of sequence
        else:
            awg.write(f'stable1:data {3 *i}, {cmd}, 1, {(i + 1) <<16 | 1 << 0}, 1, 0, #hffffffff')
            awg.write(f'stable1:data {3 * i + 1}, {data | mkr}, 1, 1, 2, 0, #hffffffff')
            awg.write(f'stable:data {3 * i + 2}, {cmd}, 0, 0, 0, {endIdleSamples}, 0')
            awg.write(f'stable1:data {3 *i + 3}, {data | end}, 1, 1, 1, 0, #hffffffff')


def main():
    """Creates a simple sine wave using digital upconversion in the M8190."""
    awg = SocketInstrument('141.121.210.171', port=5025)
    print('Connected to:', awg.instId)
    awg.write('*rst')
    awg.query('*opc?')
    awg.write('abort')

    # User-defined sample rate, carrier frequency, and interpolation factor.
    ############################################################################
    fs = 7.2e9
    cf = 100e6
    rise = 100e-9
    fall = 100e-9
    pw = 10e-6
    shape = 'trapezoidal'
    pri = 20e-6

    # Define resolution
    # Use 'intx3', 'intx12', 'intx24', or 'intx48' to enable digital up conversion mode.
    res = 'intx3'
    ############################################################################

    awg.write(f'trace1:dwidth {res}')
    res = awg.query('trace1:dwidth?').strip()
    print(f'Output res/mode: {res}')

    # Configure DUC carrier frequency.
    awg.write(f'carrier1:freq {cf}')
    print('DUC Carrier Frequency, Offset:', awg.query('carrier1:freq?'.strip()))

    # Set sample rate.
    awg.write(f'frequency:raster {fs}')
    print('Sample rate: ', awg.query('frequency:raster?'))

    # Set external reference.
    awg.write('roscillator:source axi')
    awg.write('roscillator:frequency 10e6')
    print('Reference source: ', awg.query('roscillator:source?').strip())
    print('Reference frequency: ', awg.query('roscillator:frequency?').strip())

    # Configure and enable AC output path.
    awg.write('output1:route ac')
    awg.write('output1:norm on')

    awg.write('ac1:voltage:amplitude 2.0')

    # Create waveforms required to generate pulse train and download to M8190.
    pulse, config, idle, endIdle = iq_pulse_calculator(fs, rise, fall, pw, shape, pri, res)

    # Note the divide by two here, waveform length is defined in terms of IQ PAIRS.
    awg.write(f'trace1:def 1, {len(config) / 2}')
    awg.binblockwrite('trace1:data 1, 0, ', config)
    awg.write(f'trace1:def 2, {len(pulse) / 2}')
    awg.binblockwrite('trace1:data 2, 0, ', pulse)

    # Build action table and sequence.
    freq = [980e6, 990e6, 1e9, 1.01e9, 1.02e9]
    action_table_freq_builder(awg, freq)
    pulse_sequence_builder(awg, len(freq), idle, endIdle)

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
