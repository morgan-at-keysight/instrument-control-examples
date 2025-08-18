# Author: Morgan Allison
# Updated: 2/25
# 
# Sets up Fast Power Mode, configures 20 channels,
# and sequentially captures channel power modes as quickly as possible.
#
# Obligatory warning that this software has not gone through
# the standard Keysight software development process. It was
# written by a field application engineer as a one-off example.
# 
# Python 3.12.x
# PyVISA 1.14.x
# NumPy 2.0.x

import pyvisa
import numpy as np
from time import perf_counter

def main():
    # Put your UXA's IP address here
    sa = pyvisa.ResourceManager().open_resource('TCPIP::localhost::hislip0::INSTR')
    sa.timeout = 10000 # ms
    
    # Reset the instrument and wait for reset operation to complete
    sa.write('*RST')
    sa.query('*OPC?')
    sa.write('*CLS')

    # Get instrument identifier and print it as a sanity check
    instID = sa.query('*IDN?')
    print(f'Connected to {instID}')

    ######## FPOW Measurement Setup ########
    
    # Center frequency in Hz
    cf = 10e9
    
    # For multiple channel measurements, we can use an array of offsets to fine each channel
    # Here we set up a range of offsets from -250 MHz to +250 MHz
    cf_offset_array = np.arange(-250e6, 250e6, 25e6)
    
    # The syntax of FPOW mode here requires comma separated values, 
    # so we can't just pass in an array to the "OffsetFrequency" parameter
    formatted_cf_offset_array = ','.join(map(str, cf_offset_array))
    
    # Channel bandwidth in Hz
    ch_bandwidth = 25e6
    
    # Acquisition time in seconds
    acq_time = 500e-3
    
    # Detector type, options are "Rms", "RmsAverage", "Peak", "Sample", "Average"# "Peak", "Rms", "RmsAverage", "Sample"
    detector_type = "RmsAverage" 
    
    # Resolution bandwidth mode, options are "BestResolution", "BestSpeed", "Fixed"
    rbw_mode = "BestSpeed"
    
    # Choose whether to use the preselector or not, "True" or "False"
    use_presel = "False" 
    
    # Resolution bandwidth in Hz
    rbw = 10e6
    
    # IF bandwidth in Hz
    if_bw = 500e6

    #  IF path, options are "WideBandIF", "NarrowBandIF", "WideBandRF", "NarrowBandRF"
    if_type = "WideBandIF"

    # IF bandwidth to be used, nomenclature is B<bandwidth in MHz>M "B10M", "B25M", "B40M", "B160M", "B255M", "B1000M", "B1500M", "B2000M"
    if_spec = "B1000M" 
    
    # Number of measurements to take
    num_measurements = 100

    ######## FPOW Measurement Configuration ########
    
    # Configure the normal SA mode settings
    sa.write(f':SENSe:FREQuency:CENTer {cf}')
    sa.write(f':SENSe:FREQuency:SPAN {if_bw}')

    # Configure the FPOW measurement settings
    # Always reset first
    sa.write(f':CALC:FPOW:POW1:RES')

    sa.write(f':CALC:FPOW:POW1:DEF "CenterFrequency={cf}"')
    sa.write(f':CALC:FPOW:POW1:DEF "OffsetFrequency=[{formatted_cf_offset_array}]"')
    sa.write(f':CALC:FPOW:POW1:DEF "IFType={if_type}"')
    sa.write(f':CALC:FPOW:POW1:DEF "IFSpec={if_spec}"')
    sa.write(f':CALC:FPOW:POW1:DEF "Bandwidth={ch_bandwidth}"')
    sa.write(f':CALC:FPOW:POW1:DEF "AcquisitionTime={acq_time}"')
    sa.write(f':CALC:FPOW:POW1:DEF "DetectorType={detector_type}"')
    sa.write(f':CALC:FPOW:POW1:DEF "ResolutionBWMode={rbw_mode}"')
    sa.write(f':CALC:FPOW:POW1:DEF "ResolutionBW={rbw}"')
    sa.write(f':CALC:FPOW:POW1:DEF "UsePreSelector={use_presel}"')
    
    # Query and print the FPOW definition to verify settings
    fpow_def = sa.query(f':CALC:FPOW:POW1:DEF?')
    print(f'Fast power definition:\n{fpow_def}')
    
    # Configure measurement arrays
    fpow_meas_time_array = []
    overhead_time_array = []
    fpow_array = []

    # Run the FPOW measurements
    for i in range(num_measurements):
        t0 = perf_counter()
        fpow = sa.query(f':CALC:FPOW:POW1?')
        t1 = perf_counter()

        # Calculate overhead time by subtracting the specified acquisition time from the calculated measurement time (t1 - t0)
        fpow_meas_time = t1 - t0
        overhead_time = fpow_meas_time - acq_time
        
        # Populate arrays
        fpow_array.append(fpow)
        fpow_meas_time_array.append(fpow_meas_time)
        overhead_time_array.append(overhead_time)
    
    print(fpow_meas_time_array)
    print(overhead_time_array)
    print(f'Average FPOW measurement time: {np.mean(fpow_meas_time_array)}')
    print(f'Average overhead time: {np.mean(overhead_time_array)}')

if __name__ == '__main__':
    main()
