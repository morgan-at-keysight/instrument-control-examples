"""
S2P file and Screenshot Transfer
Sets up VNA for 2 port s-parameter measurement, saves and transfers
s2p file and screenshot bmp file to controlling PC
Author: Morgan Allison
Updated: 6/2022
Windows 10
Python 3.9.x
PyVISA 1.12.x
Matplotlib 3.4.x
Tested on N5245B PNA-X
"""

import pyvisa
import matplotlib.pyplot as plt


def err_check(vna):
    """HELPER FUNCTION
    Prints out all errors and clears error queue. Raises Exception with the info of the error encountered."""

    err = []

    # Query errors and remove extra characters
    temp = vna.query('syst:err?').strip().replace('+', '').replace('-', '')

    # Read all errors until none are left
    while temp != '0,"No error"':
        # Build list of errors
        err.append(temp)
        temp = vna.query('syst:err?').strip().replace('+', '').replace('-', '')
    if err:
        raise Exception(err)


def vna_setup(vna, start=10e6, stop=26.5e9, numPoints=201, ifBw=1e3, measName=['meas1'], measParam=['S11'], ch=1, win=1):
    """Sets up basic S parameter measurement(s).

    Configures measurements and traces in a single window, sets start/stop
    frequency, number of points, IF bandwidth, and dwell time from preset state."""

    if not isinstance(measName, list) and not isinstance(measParam, list):
        raise TypeError('measName and measParam must be lists of strings, even when defining only one measurement.')

    vna.write('system:fpreset')
    vna.query('*opc?')
    vna.write(f'display:window{win}:state on')

    # Order of operations: 1-Define a measurement. 2-Feed measurement to a trace on a window.
    t = 1
    for m, p in zip(measName, measParam):
        vna.write(f'calculate{ch}:parameter:define "{m}","{p}"')
        vna.write(f'display:window{win}:trace{t}:feed "{m}"')
        t += 1

    # Configure s-parameter stimulus
    vna.write(f'sense{ch}:frequency:start {start}')
    vna.write(f'sense{ch}:frequency:stop {stop}')
    vna.write(f'sense{ch}:sweep:points {numPoints}')
    vna.write(f'sense{ch}:bandwidth {ifBw}')


def vna_get_trace(vna, measName, ch):
    """Acquires frequency and measurement data from selected measurement on VNA for plotting."""
    
    if not isinstance(measName, str):
        raise TypeError('measName must be a string.')

    # Select measurement to be transferred.
    vna.write(f'calculate{ch}:parameter:select "{measName}"')

    # Format data for transfer.
    vna.write('format:border swap')
    vna.write('format real,64')  # Data type is double/float64, not int64.

    # Acquire measurement data.
    meas = vna.query_binary_values(f'calculate{ch}:data? fdata', datatype='d')
    vna.query('*opc?')

    # Acquire frequency data.
    freq = vna.query_binary_values(f'calculate{ch}:x?', datatype='d')
    vna.query('*opc?')

    return freq, meas


def vna_get_screenshot(vna, sourcePath, destPath):
    """Saves a screenshot (MUST BE IN .bmp FORMAT) at sourcePath on the VNA and transfers it to destPath on the remote PC"""
    
    # Save screenshot on VNA hard drive
    vna.write(f'mmemory:store "{sourcePath}"')
    
    # Transfer raw bytes from file on VNA hard drive to remote PC
    rawData = vna.query_binary_values(f'mmemory:transfer? "{sourcePath}"', datatype='c')
    data = b''.join(rawData)

    # Write file to remote PC file location
    with open(destPath, mode="wb") as f:
                f.write(data)


def vna_get_s2p(vna, sourcePath, destPath):
    """Saves an s2p file at sourcePath on the VNA and transfers it to destPath on the remote PC"""
    
    # Save s2p file on VNA hard drive
    vna.write(f'mmemory:store "{sourcePath}"')    
    
    # Transfer raw bytes from file on VNA hard drive to remote PC
    rawData = vna.query_binary_values(f'mmemory:transfer? "{sourcePath}"', datatype='c')
    data = b''.join(rawData)

    # Write file to remote PC file location
    with open(destPath, mode="wb") as f:
                f.write(data)


def vna_single_trigger(vna):
    # Executes a single sweep and stops
    vna.write('initiate:continuous off')
    vna.write('initiate:immediate')
    vna.query('*opc?')


def main():
    """Configures VNA to make a single sweep, acquiring all four 2-port
    S parameters in separate traces and plots each in a separate subplot."""

    visaAddress = 'TCPIP0::127.0.0.1::hislip30::INSTR'

    vna = pyvisa.ResourceManager().open_resource(visaAddress)
    vna.timeout = 10000
    print('Connected to:', vna.query('*idn?'))

    # Measurement parameters
    ch = 1
    win = 1
    startFreq = 10e6
    stopFreq = 4e9
    numPoints = 201
    ifBw = 1e3
    measName = ['meas1', 'meas2', 'meas3', 'meas4']
    measParam = ['S11', 'S12', 'S21', 'S22']
    
    vna_setup(vna, start=startFreq, stop=stopFreq, numPoints=numPoints, ifBw=ifBw, measName=measName, measParam=measParam, ch=ch, win=win)

    # Capture a single sweep
    vna_single_trigger(vna)

    # Save s2p file
    sourceS2pFileName = 'C:\\temp\\data.s2p'
    destS2pFileName = 'C:\\temp\\data_xfer.s2p'
    vna_get_s2p(vna, sourceS2pFileName, destS2pFileName)

    # Save screenshot
    sourceScreenFileName = 'C:\\temp\\screenshot.bmp'
    destScreenFileName = 'C:\\temp\\screenshot_xfer.bmp'
    vna_get_screenshot(vna, sourceScreenFileName, destScreenFileName)

    # Acquire and plot trace data.
    plotColors = ['y', 'c', 'm', 'g']
    fig = plt.figure(figsize=(15, 8))

    for t in range(len(measName)):
        # Acquire trace data
        freq, result = vna_get_trace(vna, measName[t], ch=ch)
        # Add & format subplots and plot data
        ax = fig.add_subplot(2, 2, t + 1, facecolor='k')
        ax.plot(freq, result, c=plotColors[t])
        ax.set_title(f'Trace {t + 1}')
        ax.set_xlabel('Frequency (Hz)')
        ax.set_ylabel(f'{measParam[t]} (dB)')

    # Clean up and display plots.
    plt.tight_layout()
    plt.show()

    # Check for errors and gracefully disconnect.
    err_check(vna)
    vna.close()


if __name__ == '__main__':
    main()
