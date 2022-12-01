# Author: Morgan Allison
# Updated 12/22
# 
# This module wraps the IVI driver for Keysight PXIe microwave switches
# Tested on M9157C and M9155C running driver version 1.0.6.0


# The comtypes.client package implements all the high level functionality of comtypes
from comtypes import client

# client.GetModule() method creates a Python wrapper for the COM object (from the driver dll)
# This is apparently not strictly necessary if the COM object contains type information
# client.CreateObject() also calls client.GetModule() under the hood.
client.GetModule('C:\\Program Files\\IVI Foundation\\IVI\\Bin\\AgMWSwitch_64.dll')

# This is the Python wrapper created by GetModule. We need this to expose the interface for the COM object
from comtypes.gen import AgMWSwitchLib

class SwitchError(Exception):
    pass


class BaseSwitch():
    """Base class for controlling M9157C, M9155C, and M9161D PXIe microwave switches."""
    def __init__(self, visaAddress, idQuery=False, reset=False):
        # Remember when we needed to import the Python wrapper generated 
        # by comtypes to get the interface for client.CreateObject()? Well, here is the payoff
        # To determine what to use as the interface keyword argument, go to
        # <python directory>\Lib\site-packages\comtypes\gen\AgMWSwitchlib.py and find 
        # the long alphanumeric string in the first line. Go back into the comtypes\gen\ 
        # directory and open the file that matches the long alphanumeric string.
        # The first class definition in this file is IAgMWSwitch. The interface keyword argument
        # should be AgMWSwitchLib.IAgMWSwitch
        self.comObj = client.CreateObject('AgMWSwitch.AgMWSwitch', interface=AgMWSwitchLib.IAgMWSwitch)
        self.comObj.Initialize(visaAddress, idQuery, reset, '')

        # Get identifying information for a given switch
        self.driver = self.comObj.Identity.Identifier
        self.supportedInstruments = self.comObj.Identity.SupportedInstrumentModels
        self.instMfr = self.comObj.Identity.InstrumentManufacturer
        self.instVendor = self.comObj.Identity.Vendor
        self.instDescription = self.comObj.Identity.Description
        self.instModel = self.comObj.Identity.InstrumentModel
        self.firmwareVersion = self.comObj.Identity.InstrumentFirmwareRevision

        # Define number of available switch positions for printing bank state
        if self.instModel in ['M9155C', 'M9156C']:
            self.numPos = 2
        elif self.instModel == 'M9157C':
            self.numPos = 6
        elif self.instModel == 'M9161D':
            self.numPos = 4
        else:
            raise SwitchError(f'Model number {self.instModel} not supported by IVI driver.')

    def bank_route_checker(original_function):
        """Decorator function for checking chosen bank/route against available banks/routes for switch model."""
        def wrapper_function(self, *args, **kwargs):
            bank = kwargs['bank']
            route = kwargs['route']

            # Bank checking
            if bank < 1 or bank > 2:
                raise SwitchError('bank cannot be less than 1 or greater than 2.')
            elif self.instModel == 'M9157C' and bank > 1:
                raise SwitchError(f'{self.instModel} only supports bank = 1.')
            elif self.instModel in ['M9155C', 'M9156C', 'M9161D'] and bank > 2:
                raise SwitchError(f'{self.instModel} only supports bank = 1 or bank = 2.')
            
            # Route checking 
            if route < 1 or route > 6:
                raise SwitchError('route cannot be less than 1 or greater than 6.')
            elif self.instModel in ['M9155C', 'M9156C',] and route > 2:
                raise SwitchError(f'{self.instModel} only supports route = 1 or route = 2.')
            elif self.instModel == 'M9161D' and route > 4:
                raise SwitchError(f'{self.instModel} only supports route = 1, route = 2, route = 3, or route = 4.')
            
            return original_function(self, *args, **kwargs)
        return wrapper_function

    def PresetClear(self):
        """Presets and clears the switch module"""
        self.comObj.Utility.Reset()
        self.comObj.Utility.ErrorQuery()

    def PrintInfo(self):
        print(f'Driver: {self.driver}')
        print(f'Instrument manufacturer: {self.instMfr}')
        print(f'Instrument vendor: {self.instVendor}')
        print(f'Instrument model: {self.instModel}')
        print(f'Firmware version: {self.firmwareVersion}')
        print(f'Supported instrument models: {self.supportedInstruments}')

    @bank_route_checker
    def CloseConnection(self, bank=1, route=1):
        """Closes connection in user-specified bank and route."""
        self.comObj.Route.CloseChannel(f'b{bank}ch{route}')
    
    @bank_route_checker
    def CheckClosedConnection(self, bank=1, route=1):
        """Checks the status of closed connection in user-specified bank and route."""
        return self.comObj.Route.IsChannelClosed(f'b{bank}ch{route}')
    
    # OpenAll unavailable for transfer or SPDT switches
    def OpenAllConnections(self):
        """Opens all connections in switch module."""
        if self.instModel not in ['M9157C', 'M9161D']:
            raise SwitchError(f'OpenAllConnections not supported in {self.instModel}')
        self.comObj.Route.OpenAll()

    def BankState(self, bank=1):
        """Returns a binary bitmap of switch bank state, 0 is open and 1 is closed."""
        return bin(self.comObj.Route.GetBankState(bank)[0])[2:].zfill(self.numPos)

def switch_example():
    # Transfer
    # visaAddress = 'PXI0::CHASSIS1::SLOT16::INDEX0::INSTR'
    # SP6T
    visaAddress = 'PXI0::CHASSIS1::SLOT13::INDEX0::INSTR'
    
    # Specify bank and route
    bank = 1
    route = 3
    
    # Create switch object, preset, and print info
    switch = BaseSwitch(visaAddress)
    switch.PresetClear()
    switch.PrintInfo()

    # Close connection
    switch.CloseConnection(bank=bank, route=route)
    # switch.OpenAllConnections()

    # Print state of switch
    print(f'Bank {bank} route {route} closed? {switch.CheckClosedConnection(bank=bank, route=route)}')
    print(f'Bank {bank} state: {switch.BankState(bank=bank)}')


def main():
    switch_example()


if __name__ == '__main__':
    main()