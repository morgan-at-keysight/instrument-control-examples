# File transfer example
# Author: Morgan Allison
# Updated: 06/2022

import pyvisa


def err_check(inst):
    """HELPER FUNCTION
    Prints out all errors and clears error queue. Raises error with the info of the error encountered."""

    err = []
    cmd = 'SYST:ERR?'

    # Strip out extra characters
    temp = inst.query(cmd).strip().replace('+', '').replace('-', '')
    # Read all errors until none are left
    while temp != '0,"No error"':
        # Build list of errors
        err.append(temp)
        temp = inst.query('syst:err?').strip().replace('+', '').replace('-', '')
    if err:
        raise ValueError(err)


def read_file(inst, sourcePath, destPath):
    """Transfers file at sourcePath on the instrument to destPath on the remote PC"""
    
    # Transfer data from file on instrument hard drive as a list of raw bytes
    rawData = inst.query_binary_values(f'mmemory:data? "{sourcePath}"', datatype='c')
    # Join the raw data into a single bytes object
    data = b''.join(rawData)

    # Write file to remote PC file location as bytes
    with open(destPath, mode="wb") as f:
                f.write(data)


def write_file(inst, sourcePath, destPath, overwrite=True):
    """Transfers file at sourcePath on the remote PC to destPath on the instrument"""

    # Write file to remote PC file location as bytes
    with open(sourcePath, mode="rb") as f:
                data = f.read()
    
    # mmemory:data doesn't overwrite a file that already exists by default,
    # so delete it first with mmemory:delete
    if overwrite:
        try:
            inst.write(f'mmemory:delete "{destPath}"')
            err_check(inst)
        except ValueError as e:
            # This will only cause an error if you try to delete a file that doesn't exist.
            print(str(e))

    # Transfer binary data from file on remote PC to hard drive on the instrument
    inst.write_binary_values(f'mmemory:data "{destPath}", ', data, datatype='b')
 

def file_io_test():
    inst = pyvisa.ResourceManager().open_resource('TCPIP0::192.168.50.200::hislip0::INSTR')

    writeSourcePath = 'C:\\temp\\data_cable2.s2p'
    writeDestPath = 'C:\\temp\\data_cable2.s2p'

    write_file(inst, writeSourcePath, writeDestPath)

    readSourcePath = 'C:\\temp\\KeysightLicAgreement.txt'
    readDestPath = 'C:\\temp\\KeysightLicAgreement.txt'

    read_file(inst, readSourcePath, readDestPath)


def main():
    file_io_test()


if __name__ == "__main__":
    main()