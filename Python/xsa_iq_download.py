# Example code written by Morgan Allison
# Obligatory warning that this software has not gone through
# the standard Keysight software development process. It was
# written by a field application engineer as a one-off example.
# Python 3.9.x
# socketscpi 2020.05.0
# Matplotlib 3.4.1
# to get socketscpi and matplotlib open windows command prompt and type:
# pip install socketscpi
# pip install matplotlib


import socketscpi
import matplotlib.pyplot as plt

def main():
    """Establishes communication with X-series signal analyzer,
    configures basic settings, acquires a trace, and plots i."""

    # Measurement setup
    cf = 1e9
    refLevel = 0.125
    voltsPerDiv = 0.05
    ifBw = 500e6
    acqTime = 100e-6

    # Create an instrument object with socketscpi
    sa = socketscpi.SocketInstrument('<your IP address here>')
    # Now I can interact with the spectrum analyzer object by calling
    # .write(), .query(), .read(), etc. methods

    # Reset the instrument and wait for reset operation to complete
    sa.write('*RST')
    sa.query('*OPC?')

    # get instrument identifier
    instID = sa.query('*IDN?')
    # I'm using an f-string here, which uses {var} to insert variables into strings
    print(f'Connected to {instID}')

    # Set up IQ Analyzer mode
    sa.write(f":INSTrument:SELect BASIC")
    sa.write(f":CONFigure:WAVeform:NDEFault")
    sa.write(f":DISPlay:WAVeform:VIEW:NSELect 2")

    # Set center frequency, span, rbw, and reference level
    sa.write(f':SENSe:FREQuency:CENTer {cf}')
    sa.write(f':SENSe:WAVeform:DIF:BANDwidth {ifBw}')
    sa.write(f':SENSe:WAVeform:SWEep:TIME {acqTime}')
    sa.write(f':DISP:WAV:VIEW2:WIND:TRAC:Y:RLEV {refLevel}')
    sa.write(f':DISP:WAV:VIEW2:WIND:TRAC:Y:RPOS TOP')
    sa.write(f':DISP:WAV:VIEW2:WIND:TRAC:Y:PDIV {voltsPerDiv}')

    # Single shot, restart, wait for operation to complete
    sa.write(':INITiate:CONTinuous 0')
    sa.write(':INITiate:WAVeform')
    sa.query('*OPC?')

    # Make sure binary formatting for trace data is correct (data type and endianness)
    sa.write(':FORMat:TRACe:DATA REAL,32')
    sa.write(':FORMat:BORDer SWAPped')

    # Grab trace data (expecting 32-bit big endian floating point data)
    trace = sa.binblockread(f':FETCH:WAVeform0?', datatype='f')

    # Separate out interleaved I and Q
    i = trace[0::2]
    q = trace[1::2]

    # Plot I and Q
    plt.plot(i)
    plt.plot(q)
    plt.show()

    sa.err_check()

if __name__ == '__main__':
    main()
