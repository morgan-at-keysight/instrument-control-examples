"""
Simple Pulse Sequence Builder
Author: Morgan Allison
Updated: 06/18
Creates a single simple rectanglar RF pulse using data and idle segments in the sequencer.
Python 3.6.4
PyVISA 1.9.0
NumPy 1.14.2
Tested on M8190A
"""

import visa
import numpy as np


class awgError(Exception):
    """Generic class for AWG related errors."""
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

    # Check length and granularity requirements and calc extra samples needed.
    # Minimum length
    if pwSamples < minLen:
        extra = minLen - pwSamples
    # Granularity
    else:
        extra = gran - (pwSamples % gran)

    # Apply length and granularity corrections.
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

    return pulseOn, endWfm, idleSamples


def main():
    """CW pulse sequence creation example."""
    # Substitute your instrument's IP address here.
    awg = search_connect('TW56330445.cla.is.keysight.com')
    awg.write('*rst')
    awg.query('*opc?')
    awg.write('abort')

    # User-defined sample rate, carrier freq, pulse width, and pri.
    ############################################################################
    fs = 10e9
    cf = 100e6
    width = 10e-6
    pri = 20e-6
    ############################################################################

    # Define DAC resolution. Use 'wsp' for 12-bit and 'wpr' for 14-bit.
    res = 'wsp'
    awg.write(f'trace1:dwidth {res}')
    print(f'Output res/mode: ', awg.query('trace1:dwidth?').strip())

    # Set sample rate.
    awg.write(f'frequency:raster {fs}')
    print('Sample rate: ', awg.query('frequency:raster?').strip())

    # Configure and enable output path.
    awg.write('output1:route dac')
    awg.write('output1:norm on')

    # Create building blocks for cw pulse sequence.
    pulseOn, endWfm, idleSamples = cw_pulse_sequence(fs, cf, width, pri, res)

    # Define required waveforms and send data to AWG.
    awg.write(f'trace:def 1, {len(pulseOn)}')
    awg.write_binary_values('trace:data 1, 0, ', pulseOn, datatype='h')
    awg.write(f'trace:def 2, {len(endWfm)}')
    awg.write_binary_values('trace:data 2, 0, ', endWfm, datatype='h')

    """
    Command Documentation
    Load sequence index with wfm segment
    stable:data <seq_table_index>, <control_entry>, <seq_loop_cnt>, <seg_loop_cnt>, <seg_id>, <seg_start>, <seg_end>
    Load sequence index with idle waveform
    stable:data <seq_table_index>, <control_entry>, <seq_loop_cnt>, <command_code>, <idle_sample>, <idle_delay>, 0
    Descriptions of the command arguments (<control_entry>, <seq_loop_cnt>, etc.) can be found
    on pages 262-265 in Keysight M8190A User's Guide (Edition 13.0, October 2017).

    """
    # Build sequence.
    awg.write('seq:delete:all')
    awg.query('seq:def:new? 3')
    awg.write(f'stable1:data 0, {1 << 28}, 1, 1, 1, 0, #hffffffff')
    awg.write(f'stable1:data 1, {1 << 31}, 0, 0, 0, {idleSamples}, 0')
    awg.write(f'stable1:data 2, {1 << 30}, 0, 1, 2, 0, #hffffffff')

    # Configure AWG to output a sequence and begin playback.
    awg.write('source:func1:mode stsequence')
    awg.write('stable:seq:sel 0')
    awg.write('init:cont on')
    awg.write('init:imm')
    awg.query('*opc?')

    # Check for errors and gracefully disconnect.
    err_check(awg)
    awg.close()


if __name__ == '__main__':
    main()
