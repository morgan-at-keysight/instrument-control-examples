"""
XSA Pulse Measurement Example
Author: Morgan Allison
Updated: 03/2021
Sets up the pulse measurement on an X-series signal analyzer and successively 
makes new captures and saves the "top level" of the pulse in a text file.
Python 3.9.x
Tested on N9020B PXA
"""

import pyvisa
import matplotlib.pyplot as plt


def err_check(inst):
    """Prints out all errors and clears error queue. Raises SockInstError with the info of the error encountered."""

    err = []

    # Strip out extra characters
    temp = inst.query("syst:err?").strip().replace('+', '').replace('-', '')
    # Read all errors until none are left
    while temp != '0,"No error"':
        # Build list of errors
        err.append(temp)
        temp = inst.query('syst:err?').strip().replace('+', '').replace('-', '')
    if err:
        raise ValueError(err)

def main():
    """Sets up a pulse measurement on an x series analyzer and captures
    the 'top level' measurement values from each acquisition."""

    saIpAddress = "141.121.148.106"
    vxgIpAddress = "141.121.151.242"

    # User-definable configuration variables for specan
    cf = 1e9 # Hz
    span = 50e6 # Hz
    attenuation = 20 # dB
    measTime = 100e-6 # sec
    # trigSource = "external1"
    # trigLevel = 1 # V

    # User-definable configuration variables for VXG
    pulseWidth = 5e-6 # sec
    pulsePeriod = 10e-6 # sec
    initialPower = -10 # dB
    powerStep = 1 # dB

    numAcquisitions = 10

    fileName = "C:\\temp\\pulse-power-data.txt"

    # numPulses = 1
    trigSource = "level"
    trigLevel = -10 # dBm

    """Spectrum Analyzer Block"""
    # Connect to and preset analyzer.
    rm = pyvisa.ResourceManager()
    specan = rm.open_resource(f"TCPIP0::{saIpAddress}::hislip0::INSTR")
    print('Connected to:', specan.query("*idn?"))
    specan.write('*rst')
    specan.query("*opc?")

    # Select pulse measurement mode and set it to default
    specan.write('instrument:select pulsex')
    specan.query("*opc?")
    specan.write('configure:pulse:ndefault')
    specan.query("*opc?")

    # Configure measurement settings
    specan.write(f'sense:frequency:center {cf}')
    specan.write(f'sense:pulse:bandwidth {span}')
    specan.write('sense:power:attenuation:auto off')
    specan.write(f"sense:power:attenuation {attenuation}")
    specan.write(f"sense:pulse:time:length {measTime}")
    
    # Trigger is not required for this measurement, but can be used by uncommenting the following two lines
    # specan.write(f"trigger:pulse:source {trigSource}")
    # specan.write(f"trigger:{trigSource}:level {trigLevel}")

    # Optionally, uncomment the following two lines to limit the measurement to a single pulse.
    # specan.write(f"calculate:pulse:select:length {numPulses}")
    # specan.write(f"calculate:pulse:select:all off")
    
    specan.query('*opc?')

    """Signal Generator Block"""
    # Connect to and preset signal generator
    vxg = rm.open_resource(f"TCPIP0::{vxgIpAddress}::hislip1::INSTR")
    print("Connected to:", vxg.query("*idn?"))
    vxg.write("*rst")
    vxg.query("*opc?")

    vxg.write(f"rf2:frequency {cf}")
    vxg.write(f"rf2:power {initialPower}")
    vxg.write(f"rf2:pulm:source internal")
    vxg.write(f"rf2:pulm:source:internal frun")
    vxg.write(f"rf2:pulm:internal:pwidth {pulseWidth}")
    vxg.write(f"rf2:pulm:internal:period {pulsePeriod}")

    vxg.write("source:rf2:pulm:state on")
    vxg.write("source:rf2:output:state on")

    """Acquisition Loop"""
    specan.write('initiate:continuous off')
    outputPower = []
    inputPower = []

    for i in range(numAcquisitions):
        # Set VXG power level and append to "input power" list
        genPower = initialPower + i * powerStep
        inputPower.append(genPower)
        vxg.write(f"source:rf2:power {genPower}")
        vxg.query("*opc?")

        # Set up and execute a single-shot acquisition and measurement.
        specan.write('initiate:immediate')
        specan.query('*opc?')

        # Query pulse "top level" values
        # The instrument returns a comma separated list of power values
        topLevel = specan.query("calculate:pulse:table? tlevel")
        # Grab only the first pulse in the acquisition and convert it to a floating point value
        firstPulse = float(topLevel.split(",")[0])
        # Append pulse power to "output power" list
        outputPower.append(firstPulse)

    # Save results to file
    with open(fileName, "w+") as f:
        # Write file header
        f.write("Input Power (dBm), Output Power (dBm)\n")
        # Write each pulse power value on its own line in the file
        for i, o in zip(inputPower, outputPower):
            f.write(f"{str(i)},{str(o)}\n")

    # Plot out results
    plt.plot(inputPower, outputPower)
    plt.title("Output Power vs Input Power")
    plt.xlabel("Input Power (dBm)")
    plt.ylabel("Output power (dBm)")
    plt.show()

    # Check for errors and gracefully disconnect.
    err_check(specan)
    specan.close()

    err_check(vxg)
    vxg.close()


if __name__ == '__main__':
    main()
