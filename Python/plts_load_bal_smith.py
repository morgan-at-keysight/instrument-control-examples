"""
PLTS Diff TDR Data Load Example
Author: Morgan Allison, Keysight RF/uW Application Engineer
Tested on PLTS 2020
"""

import visa


def main():
    rm = visa.ResourceManager()
    plts = rm.open_resource('TCPIP0::localhost::hislip3::INSTR')
    plts.timeout = 10000

    print(f'Connected to {plts.query("*idn?")}')

    files = plts.query('file:catalog?')

    try:
        # This is a weird one-liner, but it removes the whitespace and double-quotes
        # from the 'file:catalog?' return value and then turns the numbers into a list
        files = [int(f) for f in files.strip().strip('"').split(',')]
        # print(files)

        for f in files:
            plts.write(f'file{f}:close')
    # The one-liner will throw a ValueError if the returned value is an empty string,
    # which would mean there are no files open and there is no need to close them.
    except ValueError:
        pass

    dataFile = 'C:\\Program Files\\Keysight\\PLTS2020\\Data\\AFR\\Rogers_SL_Diff_stdThru.s4p'
    plts.write(f'import "{dataFile}", "Frequency Domain (Balanced)"')
    plts.query('*opc?')

    # Clear all plots
    fileNum = 1
    viewNum = 1
    plts.write(f'file{fileNum}:view{viewNum}:clear')
    # Create new plot (differential time domain)
    plts.write(f'file{fileNum}:view{viewNum}:nplot "SDD11", FBAL')
    plts.write(f'file{fileNum}:view{viewNum}:plot1:ntrace "SDD22"')

    # Configure plot format
    plts.write(f'file{fileNum}:view{viewNum}:plot1:format smith')

    # # Autoscale plot
    # plts.write(f'file{fileNum}:view{viewNum}:plot1:scale:auto')

    # Name the plot
    plotName = 'Balanced Smith Chart Impedance'
    plts.write(f'file{fileNum}:view{viewNum}:plot1:name "{plotName}"')

    # Name and save template
    templateName = 'Balanced Smith Chart Impedance'
    plts.write(f'file{fileNum}:view{viewNum}:template:save "{templateName}"')

    # Check for errors
    print(plts.query('syst:err?'))


if __name__ == '__main__':
    main()
