# VNA Trace Memory Example
# Author: Morgan Allison
# Updated: 06/2022

import pyvisa

def add_memory_to_all_traces():
    """Saves trace data to memory and changes display to Data and Memory FOR ALL TRACES"""

    vna = pyvisa.ResourceManager().open_resource('TCPIP0::127.0.0.1::hislip30::INSTR')

    # Get all the active channels on the VNA
    rawChannels = vna.query(f'system:channels:catalog?').strip('"\n')
    channels = [int(w) for w in rawChannels.split(',')]

    # Iterate through channels, get all traces per channel, and save them to memory
    for ch in channels:
        rawTraces = vna.query(f'system:measure:catalog? {ch}').strip('"\n')
        traces = [int(w) for w in rawTraces.split(',')]

        # Save traces to memory
        for t in traces:
            vna.write(f'calculate:measure{t}:math:memorize')

    # Change display type to Data and Memory for all traces in each window
    rawWindows = vna.query(f'display:catalog?').strip('"\n')
    windows = [int(w) for w in rawWindows.split(',')]

    # Iterate through windows
    for w in windows:
        rawWinTraces = vna.query(f'display:window{w}:catalog?').strip('"\n')
        traces = [int(t) for t in rawWinTraces.split(',')]
        
        # Turn data and memory traces 
        for t in traces:
            vna.query('*opc?')
            vna.write(f'display:window{w}:trace{t}:state on')
            vna.write(f'display:window{w}:trace{t}:memory:state on')


def main():
    add_memory_to_all_traces()


if __name__ == '__main__':
    main()