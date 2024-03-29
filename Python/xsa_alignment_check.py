# Author: Morgan Allison
# Updated: 05/22
# This script checks alignment status and runs only the alignments that have expired.
# Tested on N9020B
# PyVISA 1.12.x

import pyvisa
import time

# Create instrument object
visaAddress = 'TCPIP0::192.168.50.200::hislip0::INSTR'
rm = pyvisa.ResourceManager()
xsa = rm.open_resource(visaAddress)

# Set alignments to PARTIAL, which only runs critical alignment routines and prioritizes
# throughput over amplitude accuracy. There is not a dramatic reduction in accuracy.
xsa.write('calibration:auto partial')

# Check alignment status
# Bit 14 of the questionable calibration register indicates if Align now All is needed
# Bit 12 of the questionable calibration register indicates if Align now RF is needed
# We will check both
alignAllNeeded = int(xsa.query('status:questionable:calibration:condition?')) & (1 << 14)
alignRFNeeded = int(xsa.query('status:questionable:calibration:condition?')) & (1 << 12)

# alignAllNeeded and alignRFNeeded will either be 1 << 14/1 << 12 or 0
# If either variable has a non-zero value, it means the respective bit in the status register is high
# and alignment is needed
if alignAllNeeded != 0 or alignRFNeeded != 0:
    # The command below is a NON BLOCKING command, which means it doesn't pause operation until it's complete
    # This is actually helpful for us because we can poll a status register to see when it's finished.
    # This is preferable to temporarily setting a long timeout and waiting until the whole thing is done.
    xsa.write('calibration:all:npending')

    # Bit 0 of the operation status register is set to 1 while the instrument is calibrating/aligning.
    # So we can query the whole register, which is a 16 bit value and mask bit 0 to check cal/align status.
    while int(xsa.query('status:operation:condition?')) & 1 == 1:
        print('Still calibrating. Please stand by.')
        time.sleep(10)

    # We can then check the calibration status register to see if there were any issues with the alignment
    calStatus = int(xsa.query('status:questionable:calibration:condition?'))
    if calStatus:
        raise Exception(f'Calibration had an issue. Status code {calStatus}')
        # You could write a chain of if statements here to raise an exception based on which bits are set
else:
    print('No alignments needed. Carry on.')

xsa.close()
del xsa