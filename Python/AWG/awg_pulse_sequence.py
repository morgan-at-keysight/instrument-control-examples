"""
Simple Pulse Sequence Builder for Keysight AWGs
Author: Morgan Allison
Updated: 05/18
Creates a single simple rectanglar RF pulse using data and idle segments in the sequencer.
Python 3.6.4
PyVISA 1.9.0
NumPy 1.14.2
Tested on M8190A
"""

import visa
import numpy as np


def search_connect(ipAddress):
    """Configures and returns instrument VISA object using its IP address."""
    rm = visa.ResourceManager()
    inst = rm.open_resource('TCPIP0::{}::inst0:INST'.format(ipAddress))
    inst.timeout = 10000
    inst.write('*cls')
    print('Connected to {}'.format(inst.query('*idn?')))
    return inst


def err_check(inst):
    """Checks for and prints out all errors in error queue."""
    while inst.query('*esr?') != '0\n':
        print(inst.query('syst:err?'))
    print(inst.query('syst:err?'))


def check_wfm(wfm, res='WPR'):
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
        raise ValueError('Invalid output resolution selected. Choose \'wpr\' for 14 bits or \'wsp\' or 12 bits.')

    rl = len(wfm)
    if rl < minLen:
        raise ValueError('Waveform must be at least 240 samples.')
    if rl % gran != 0:
        raise ValueError('Waveform must have a granularity of 48.')

    return np.array(binMult * wfm, dtype=np.int16) << binShift


def cw_pulse_sequence(fs, cf, pwTime, pri, res='wpr'):
    """Defines sequence parameters for outputting a single RF pulse using data
    and idle segments in the sequencer. Checks and corrects for minimum wfm
    length and granularity based on DAC output resolution."""

    if res.lower() == 'wpr':
        gran = 48
        minLen = 240
    elif res.lower() == 'wsp':
        gran = 64
        minLen = 320

    # Create simple rectangular pulse.
    pwSamples = int(fs * pwTime)
    tOn = np.linspace(0, pwTime, pwSamples)
    pulseOn = np.sin(2 * np.pi * cf * tOn)

    # Check length and granularity requirements and calc extra samples needed
    # Minimum length
    if pwSamples < minLen:
        extra = minLen - pwSamples
    # Granularity
    else:
        extra = gran - (pwSamples % gran)

    # Apply len/gran corrections
    pulseOn = np.append(pulseOn, np.zeros(extra))
    pulseOn = check_wfm(pulseOn, res)

    """
    The 'Idle' segment is a special waveform in the sequencer that allows the user
    to repeat a single DAC value with single-sample granularity. A sequence cannot
    begin or end with an Idle segment, so an 'endcap' waveform must be defined to
    satisfy this requirement.
    Note, the minimum Idle duration is 3 sync clock cycles, which changes
    depending on the output sample rate.
    """

    endWfm = check_wfm(np.zeros(minLen), res)
    idleSamples = (fs * pri) - len(pulseOn) - len(endWfm)
    if idleSamples < 3 * gran / fs:
        print('Minimum idle time not satisfied. Unexpected trig-to-output behavior likely.')

    # print('Extra length: {} samples, {} seconds.'.format(extra, extra / fs))
    # print('Total length of pulse on: {} samples, {} seconds.'.format(len(pulseOn), len(pulseOn) / fs))
    # print('Effective off time: ', (idleSamples + len(endWfm) + extra) / fs)

    return pulseOn, endWfm, idleSamples


def main():
    awg = search_connect('TW56330490.cla.is.keysight.com')
    awg.write('*rst')
    awg.query('*opc?')
    awg.write('abort')

    # Define a waveform.
    res = 'wsp'     # use 'wsp' for 12-bit and 'wpr' for 14-bit

    awg.write('trace:dwidth {}'.format(res))
    res = awg.query('trace:dwidth?').strip()
    print('Output res/mode: {}'.format(res))

    fs = 7.2e9
    cf = 100e6
    width = 1e-6
    pri = 10.153e-6

    pulseOn, endWfm, idleSamples = cw_pulse_sequence(fs, cf, width, pri, res)

    awg.write('trace:def 1, {}'.format(len(pulseOn)))
    awg.write_binary_values('trace:data 1, 0, ', pulseOn, datatype='h')
    awg.write('trace:def 2, {}'.format(len(endWfm)))
    awg.write_binary_values('trace:data 2, 0, ', endWfm, datatype='h')

    awg.write('seq:delete:all')
    awg.query('seq:def:new? 3')

    """
    Command Documentation
    Load sequence index with wfm segment
    stable:data <seq_table_index>, <control_entry>, <seq_loop_cnt>, <seg_loop_cnt>, <seg_id>, <seg_start>, <seg_end>
    Load sequence index with idle waveform
    stable:data <seq_table_index>, <control_entry>, <seq_loop_cnt>, <command_code>, <idle_sample>, <idle_delay>, 0
    Descriptions of the command arguments (<control_entry>, <seq_loop_cnt>, etc.) can be found
    on pages 262-265 in Keysight M8190A User's Guide (Edition 13.0, October 2017).
    """
    awg.write('stable:data 0, {}, 1, 1, 1, 0, #hffffffff'.format(1 << 28))
    awg.write('stable:data 1, {}, 0, 0, 0, {}, 0'.format(1 << 31, idleSamples))
    awg.write('stable:data 2, {}, 0, 1, 2, 0, #hffffffff'.format(1 << 30))

    awg.write('source:func:mode stsequence')

    # Configure and enable on output path.
    awg.write('output1:route dac')
    awg.write('output:norm on')
    # print('Output path: {}'.format(awg.query('output1:route?')))

    # Assign sequence 0 to channel 1 and start continuous playback.
    awg.write('stable:seq:sel 0')
    awg.write('init:cont on')
    awg.write('init:imm')
    awg.query('*opc?')

    err_check(awg)


if __name__ == '__main__':
    main()
