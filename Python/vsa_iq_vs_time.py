"""
VSA IQ vs Time Example
Author: Morgan Allison
Updated: 11/24
Sets up a basic vector measurement in VSA, configures an external trigger,
acquires data, transfers the Main Time traces, and plots them.
Python 3.10.x
Tested on N9030B PXA and N9032B PXA
"""

import pyvisa
import matplotlib.pyplot as plt

def main():
    # User-definable configuration variables
    cf = 5e9
    span = 20e6
    vRange = 0 # dBm
    extTrigLevel = 1.3 # Volts
    trigDelay = -10e-6
    acquisitionTime = 20e-6

    # Connect to VSA. Enter the VISA address of your VSA instance below
    vsa = pyvisa.ResourceManager().open_resource('TCPIP0::localhost::hislip70::INSTR', open_timeout=10000)
    vsa.timeout = 10000 # ms
    
    # Optional code to start VSA if it isn't launched
    # vsa.write(':SYSTem:VSA:STARt')
    # print(vsa.query('system:vsa:start?'))
    # vsa.write('system:vsa:window:show 3')
    
    print('Connected to:', vsa.query('*idn?'))
    # Reset VSA, wait for preset to finish, and pause acquisition
    vsa.write('system:preset')
    vsa.query('*opc?')
    vsa.write('initiate:pause')

    # Configure vector measurement (Trace 1 = I, Trace 2 = Q, and Trace 3 = IQ/constellation)
    vsa.write('measure:nselect 1')
    vsa.write('measure:configure vector')
    vsa.write('trace1:data:name "Main Time1"')
    vsa.write('trace1:format "Real"')
    vsa.write('trace2:data:name "Main Time1"')
    vsa.write('trace2:format "Imaginary"')
    vsa.write('trace:add')
    vsa.write('trace3:data:name "Main Time1"')
    vsa.write('trace3:format "IQ"')

    # Configure center frequency & span in Hz and vertical range in dBm
    vsa.write(f'sense:frequency:center {cf}')
    vsa.write(f'sense:frequency:span {span}')
    vsa.write(f'input:analog:range:dbm {vRange}')

    # Configure external trigger
    vsa.write('input:trigger:style "External"')
    vsa.write(f'input:trigger:level {extTrigLevel}')

    # Configure mangitude level trigger
    # vsa.write('input:trigger:style "MagnitudeLevel"') # Magnitude level trigger
    # vsa.write(f'input:trigger:level {trigLevel}')

    # Configure free run trigger
    # vsa.write('input:trigger:style "Auto"') # Free run trigger
    vsa.write(f'input:trigger:delay {trigDelay}')

    # Configure acquisition time
    vsa.write('sense:rbw:points:auto 1')
    vsa.write(f'sense:time:length {acquisitionTime}')

    # Set up and execute a single-shot acquisition and measurement
    vsa.write('initiate:continuous off')
    vsa.write('initiate:immediate')
    vsa.query('*opc?')

    # Configure and prepare for data transfer
    vsa.write('format:trace:data real64')  # This is float64/double, not int64
    traces = int(vsa.query('trace:count?').strip())
    
    # Comment out this line if you don't want to plot
    fig, ax = plt.subplots(nrows=traces, figsize=(12, 9))

    # Loop through all traces, grab data/metadata, and plot
    for t in range(1, traces + 1):
        # vsa.query(f'trace{t}:data:valid?')
        vsa.write(f'trace{t}:x:autoscale 1')
        vsa.write(f'trace{t}:y:autoscale 1')
        name = vsa.query(f'trace{t}:format?').strip()
        xUnit = vsa.query(f'trace{t}:x:scale:unit?').strip()
        yUnit = vsa.query(f'trace{t}:y:scale:unit?').strip()

        # VSA uses big endian byte ordering on my computer, you may change is_big_endian to False if needed
        x = vsa.query_binary_values(f'trace{t}:data:x?', datatype='d', is_big_endian=True)
        y = vsa.query_binary_values(f'trace{t}:data:y?', datatype='d', is_big_endian=True)

        # Comment out this portion if you don't want to plot
        ax[t - 1].plot(x, y)
        ax[t - 1].set_title(name)
        ax[t - 1].set_xlabel(xUnit)
        ax[t - 1].set_ylabel(yUnit)
    
    # Comment out these two lines if you don't want to plot
    plt.tight_layout()
    plt.show()

    # Check for errors and gracefully disconnect.
    print(vsa.query('syst:err?'))
    vsa.close()


if __name__ == '__main__':
    main()
