"""
Phase Coherent Radar Pulse Generator
Author: Morgan Allison
Updated: 06/18
Calculates the coherent phase shift of a pulsed RF signal based on sample rate,
carrier frequency, and pulse repetition interval and creates a sequence with
data and idle segments resulting in a phase coherent radar pulse train.
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


class phaseCoherentError(Exception):
    """Generic class for phase calculation related errors."""
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


def phase_shift_calculator(cf, pri, fs):
    """Calculate the phase shift (deg) between pulses assuming phase coherence. 1 deg resolution.
    dPhi = omega * t where omega = 2 * pi * carrier frequency."""
    absPhase = round(cf * pri * 360, 1)
    relPhase = round(absPhase % 360, 1)
    return relPhase, cycle_calculator(relPhase)


def cycle_calculator(relPhase):
    """Calculates number of cycles required for complete modulo 360 phase wrap."""
    cycles = 1
    while (relPhase * cycles % 360) != 0:
        cycles += 1
    if cycles > 3600:
        raise phaseCoherentError('Phase coherency cycle calculation failed to converge.')
    return cycles


def cw_pulse_sequence_coherent(fs, cf, pwTime, pri, res='wsp'):
    """Builds a sequence that outputs a phase coherent pulse train."""
    if res.lower() == 'wpr':
        gran = 48
        minLen = 240
    elif res.lower() == 'wsp':
        gran = 64
        minLen = 320
    else:
        raise awgError('Invalid output resolution selected. Choose \'wpr\' for 14 bits or \'wsp\' or 12 bits.')

    # Check length and granularity requirements and calc extra samples needed.
    pwSamples = int(fs * pwTime)
    tOn = np.linspace(0, pwTime, pwSamples, endpoint=False)

    # Minimum length
    if pwSamples < minLen:
        extra = minLen - pwSamples
    # Granularity
    else:
        extra = gran - (pwSamples % gran)

    # Calculate pulse-pulse phase shift and number of pulses required for full wraparound.
    deltaPhi, numPulses = phase_shift_calculator(cf, pri, fs)
    print(f'deltaPhi per PRI: {deltaPhi}\nPulses needed for wraparound: {numPulses}')

    # Preallocate array that will hold pulse waveforms and fill array with pulses.
    pulses = np.zeros((numPulses, pwSamples + extra), dtype=np.int16)
    for p in range(numPulses):
        temp = np.append(np.sin(2 * np.pi * cf * tOn + (p * deltaPhi * 2 * np.pi / 360)), np.zeros(extra))
        pulses[p] = check_wfm(temp, res)
        # Create marker signal for first pulse.
        if p == 0:
            marker = np.append(1 * np.ones(int(len(temp) / 2)), np.zeros(int(len(temp) / 2)))
            pulses[p] = pulses[p] + marker

    # Build pulse off time waveform and idle segments.
    # endWfm exists because an idle segment cannot be the first or last segment in a sequence.
    endWfm = check_wfm(np.zeros(minLen), res)
    idleSamples = round((fs * pri) - pulses.shape[1])
    endIdleSamples = idleSamples - len(endWfm)
    if idleSamples < 3 * gran / fs:
        print('Minimum idle time not satisfied. Unexpected trig-to-output behavior likely.')

    return pulses, endWfm, idleSamples, endIdleSamples


def main():
    """Coherent pulse creation example."""
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
    pri = 20.0025e-6
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

    # Configure marker output.
    awg.write('marker:sample:voltage:high 0.5')
    awg.write('marker:sample:voltage:low 0')

    # Configure external reference.
    # A common source/analyzer reference is critical to accurately measure pulse-to-pulse phase.
    awg.write('roscillator:source ext')
    awg.write('roscillator:frequency 10e6')
    print('Reference source: ', awg.query('roscillator:source?').strip())

    # Build components for phase coherent sequence.
    pulses, endWfm, idleSamples, endIdleSamples = cw_pulse_sequence_coherent(fs, cf, width, pri, res)

    # Reset sequencer.
    awg.write('seq:delete:all')
    awg.query(f'seq:def:new? {2 * pulses.shape[0] + 1}')

    """
    COMMAND DOCUMENTATION: stable:data
    Load sequence index with wfm segment
    stable:data <seq_table_index>, <control_entry>, <seq_loop_cnt>, <seg_loop_cnt>, <seg_id>, <seg_start>, <seg_end>

    Load sequence index with idle waveform
    stable:data <seq_table_index>, <control_entry>, <seq_loop_cnt>, <command_code>, <idle_sample>, <idle_delay>, 0

    Descriptions of the command arguments (<control_entry>, <seq_loop_cnt>, etc.) can be found
    on pages 262-265 in Keysight M8190A User's Guide (Edition 13.0, October 2017).
    """

    # Build sequence.
    for i in range(len(pulses)):
        awg.write(f'trace1:def {i + 1}, {len(pulses[i])}')
        awg.write_binary_values(f'trace1:data {i + 1}, 0, ', pulses[i], datatype='h')

        # Configure data segment.
        # If start of sequence, send start-of-sequence (bit 28) and marker enable (bit 24) control entries.
        if i == 0:
            awg.write(f'stable:data 0, {1 << 28 | 1 << 24}, 1, 1, 1, 0, #hffffffff')
        # Otherwise, send waveform data with 0 control entry.
        else:
            awg.write(f'stable:data {2 * i}, 0, 0, 1, {i + 1}, 0, #hffffffff')

        # Configure Idle segment(s).
        # If sending final pulse, create a smaller idle waveform and add the ending waveform.
        if i == len(pulses) - 1:
            awg.write(f'stable:data {2 * i + 1}, {1 << 31}, 0, 0, 0, {endIdleSamples}, 0')

            awg.write(f'trace:def {i + 2}, {len(endWfm)}')
            awg.write_binary_values(f'trace:data {i + 2}, 0, ', endWfm, datatype='h')

            awg.write(f'stable:data {2 * i + 2}, {1 << 30}, 0, 1, {i + 2}, 0, #hffffffff')
        # Otherwise, create idle sequence normally in the middle of the sequence.
        else:
            awg.write(f'stable:data {2 * i + 1}, {1 << 31}, 0, 0, 0, {idleSamples}, 0')

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
