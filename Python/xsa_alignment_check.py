import pyvisa
import time


def main():
    # create instrument
    visaAddress = 'TCPIP0::192.168.50.200::hislip0::INSTR'
    rm = pyvisa.ResourceManager()
    xsa = rm.open_resource(visaAddress)

    # Check alignment status
    # Bit 14 of the questionable calibration register indicates if Align now All is needed
    # Bit 12 of the questionable calibration register indicates if Align now RF is needed
    # We will check both
    alignAllNeeded = int(xsa.query('status:questionable:calibration:condition?')) & (1 << 14)
    alignRFNeeded = int(xsa.query('status:questionable:calibration:condition?')) & (1 << 12)

    # If either are 1, run the calibration
    if alignAllNeeded == 1 or alignRFNeeded == 1:
        # The command below is a NON BLOCKING command, which means it doesn't pause operation until it's complete
        # This is actually helpful for us because we can poll a status register to see when it's finished.
        # This is preferable to temporarily setting a long timeout and waiting until the whole thing is done.
        xsa.write('calibration:all:npending')

        # Bit 0 of the operation status register is set to 1 while the instrument is calibrating/aligning.
        # So we can query the whole register, which is a 16 bit value and mask bit 0 to check cal/align status.
        while int(xsa.query('status:operation:condition?')) & 1 == 1:
            print('still calibrating')
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

if __name__ == "__main__":
    main()