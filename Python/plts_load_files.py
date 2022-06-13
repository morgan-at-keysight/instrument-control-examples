"""
PLTS Import Data Example
Author: Morgan Allison, Keysight RF/uW Application Engineer
Updated: 06/2022
Tested on PLTS 2021 Update 1
"""

import pyvisa

def err_check(plts):
    """HELPER FUNCTION
    Prints out all errors and clears error queue. Raises Exception with the info of the error encountered."""

    err = []

    # Query errors and remove extra characters
    temp = plts.query('syst:err?').strip().replace('+', '').replace('-', '')

    # Read all errors until none are left
    while temp != '0,"No error"':
        # Build list of errors
        err.append(temp)
        temp = plts.query('syst:err?').strip().replace('+', '').replace('-', '')
    if err:
        raise Exception(err)

def load_balanced_freq_domain(plts, dataFile, fileNum=1, viewNum=1):
    # Import one of the data files included in PLTS in Balanced Frequency domain format
    plts.write(f'import "{dataFile}", "Frequency Domain (Balanced)"')
    plts.query('*opc?')

    # Clear all plots
    fileNum = 1
    viewNum = 1
    plts.write(f'file{fileNum}:view{viewNum}:clear')
    
    # Create new plot (frequency domain, balanced)
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


def load_diff_time_domain(plts, dataFile, fileNum=1, viewNum=1):
    # Import one of the data files included in PLTS in Differential Time Domain format
    plts.write(f'import "{dataFile}", "Time Domain (Differential)"')
    plts.query('*opc?')

    # Clear all plots
    plts.write(f'file{fileNum}:view{viewNum}:clear')


    # Create new plot (differential time domain)
    plts.write(f'file{fileNum}:view{viewNum}:nplot "TDD11", TDIF')
    plts.write(f'file{fileNum}:view{viewNum}:plot1:ntrace "TDD22"')

    # Configure plot format
    plts.write(f'file{fileNum}:view{viewNum}:plot1:format sin')

    # Autoscale plot
    plts.write(f'file{fileNum}:view{viewNum}:plot1:scale:auto')

    # Name the plot
    plotName = 'Diff TDR Impedance'
    plts.write(f'file{fileNum}:view{viewNum}:plot1:name "{plotName}"')

    # Name and save template
    templateName = 'Diff TDR Impedance'
    plts.write(f'file{fileNum}:view{viewNum}:template:save "{templateName}"')



def main():
    # Create VISA object for PLTS
    rm = pyvisa.ResourceManager()
    plts = rm.open_resource('TCPIP0::localhost::hislip3::INSTR')
    plts.timeout = 10000

    print(f'Connected to {plts.query("*idn?")}')

    """This section closes all the open files before doing anything else"""
    # Get a list of all files
    files = plts.query('file:catalog?')

    try:
        # This is a weird one-liner, but it removes the whitespace and double-quotes
        # from the 'file:catalog?' return value and then turns the numbers into a list
        files = [int(f) for f in files.strip().strip('"').split(',')]

        # Close all the files in the list
        for f in files:
            plts.write(f'file{f}:close')
    # The one-liner will throw a ValueError if the returned value is an empty string,
    # which would mean there are no files open and there is no need to close them.
    except ValueError:
        print(f'No files open, nothing to close.')

    dataFile = 'C:\\Program Files\\Keysight\\PLTS2021U1\\Data\\AFR\\Rogers_SL_Diff_stdThru.s4p'
    load_balanced_freq_domain(plts, dataFile, fileNum=1)
    load_diff_time_domain(plts, dataFile, fileNum=2)

    # Check for errors
    err_check(plts)


if __name__ == '__main__':
    main()
