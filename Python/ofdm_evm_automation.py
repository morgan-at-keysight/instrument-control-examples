import pyarbtools
import numpy as np
import matplotlib.pyplot as plt

def full_generate_demod(analyzer='vma', vxgIpAddress="192.168.50.22", saIpAddress="192.168.50.3"):
    """
    This function automates the loading and playback of a waveform created by Keysight N7608C Signal Studio for Custom Modulation
    into an M9384B VXG signal generator and demodulation/analysis on a Keysight X-series signal analyzer with the N9054EM0E
    Vector Modulation Analysis option.
    """
    # This is the base waveform filename. It does not have a file extension associated with it.
    # File extension will be added by the appropriate steps in this script
    # wfmBaseFileName = "D:\\Users\\Instrument\\Desktop\\Morgan\\400MHz-cp-ofdm-longer-cp"
    wfmBaseFileName = "D:\\Users\\Instrument\\Desktop\\Morgan\\500MHz-cp-ofdm-longer-cp"

    # vxg object creation
    vxg = pyarbtools.instruments.VXG(vxgIpAddress)
    
    # Append appropriate file extension to baseWfmFileName and load signal studio waveform file into VXG
    wfmPath = f'{wfmBaseFileName}.wfm'
    vxg.write(f'source:signal:waveform:select "{wfmPath}"')

    
    # Configure VXG, and begin playback
    # Waveform setup parameters
    cf = 18e9
    amp = -20
    span = 1e9

    vxg.configure(cf1=cf, amp1=amp, arbState=1, rfState=1, modState=1)

    # IQ calibration
    ch = 1
    vxg.socket.settimeout(30)
    vxg.write(f":SOURce:RF{ch}:CALibration:IQ:DC")
    vxg.query("*opc?")
    # # vxg.write(f":SOURce:RF{ch}:CALibration:IQ:TSKew")
    # # vxg.query("*opc?")
    vxg.socket.settimeout(10)

    """#####################################################################"""
    if analyzer.lower() == 'vsa':
        # VSA object creation and preset
        hw = "Analyzer1"
        vsa = pyarbtools.vsaControl.VSA(saIpAddress, port=5026, vsaHardware=hw)
        vsa.write('*rst')
        vsa.query("*opc?")

        # Append appropriate file extension to baseWfmFileName and load into VSA
        setxPath = f'{wfmBaseFileName}.setx'

        vsa.custom_ofdm_format_setup(setupFile=setxPath)
        vsa.query("*opc?")
        vsa.set_data_source(fromHardware=True)
        vsa.set_cf(cf=cf)

        # equalizer and tracking setup
        vsa.custom_ofdm_equalizer_setup(useData=False, useDCPilot=False, usePilot=True, usePreamble=False)
        vsa.custom_ofdm_tracking_setup(useData=False, amplitude=True, phase=True, timing=False)

        # Configure signal generator power levels and optimized attenuator/if gain settings for analyzer
        # These will be used for the power sweep loop example
        sigPowerList = [-20, -10, 0, 10, 15]
        
        """This section is not needed anymore since the VSA Beta release"""
        # This set is for the 400 MHz signal on PXA
        # attenList = [0, 0, 0, 20, 30]
        # ifGainList = [4, -8, -16, -10, 10]

        # This set is for the 500 MHz signal on PXA
        # attenList = [0, 0, 6]
        # ifGainList = [-4, -14, -16]

        # This set is for the 400 MHz signal on N9042B
        # attenList = [0, 0, 0, 10, 20]
        # ifGainList = [4, -8, -16, -12, -12]

        # This set is for the 500 MHz signal on N9042B
        # attenList = [0, 0, 6, 10, 20]
        # ifGainList = [-4, -14, -16, -12, -12]

        # Empty list that will contain EVM values
        bathtub = []

        # for p, a, i in zip(sigPowerList, attenList, ifGainList):
        for p in sigPowerList:
            # Set optimal attenuation and IF gain for specific wfm and sig gen output power
            # vsa.set_attenuation(atten=a)
            # vsa.set_if_gain(ifGain=i)

            # Set sig gen output power
            vxg.configure(amp=p)
    
            # Put VSA in continuous acquisition mode
            vsa.acquire_continuous()
            vsa.query('*opc?')

            # Temporarily set a long timeout, execute the EVM optimization, and set timeout back
            vsa.socket.settimeout(60000)
            vsa.write("input:analog:criteria:range:auto 'EvmAlgorithm', 60000")
            vsa.query('*opc?')
            vsa.socket.settimeout(10000)
            
            # Optionally, keep track of the automatic attenuation and IF gain states chosen by the EVM optimization
            autoAtten = vsa.query('input:extension:parameters:get? "RangeInformationMechAtten"')
            autoIfGain = vsa.query('input:extension:parameters:get? "RangeInformationIFGain"')

            # Make single acquisition
            vsa.acquire_single()
            
            # Configure results acquisiton formatting 
            ofdmResultsTraceNum = 4
            measList = vsa.query(f'trace{ofdmResultsTraceNum}:data:table:name?').strip().replace('"','').split(',')

            # Query each measurement and build a dictionary with the measurement name and value.
            for name in measList:
                try:
                    meas = float(vsa.query(f'trace{ofdmResultsTraceNum}:data:table? "{name}"').strip())
                    unit = vsa.query(f'trace{ofdmResultsTraceNum}:data:table:unit? "{name}"').strip()
                    # print(f"{name}: {meas}")
                    
                    # This is the % EVM to dB conversion
                    if name == 'Ch1EVM':
                        meas = 20 * np.log10(meas / 100)
                        # Append the EVM value to the bathtub curve array
                        bathtub.append(meas)

                # This error check triggers when the float() call fails on non-numeric data like '***'
                # These names and associated measurements are exluded from the dictionary
                # The print statements are there for debugging and they can be replaced with the pass statement in production
                except ValueError as e:
                    pass
                    # print(f"Error in {name}")
                    # print(str(e))

        # Plot results
        plt.plot(sigPowerList, bathtub)
        plt.title('Bathtub curve')
        plt.xlabel('Signal Generator Power (dBm)')
        plt.ylabel('EVM (dB)')
        plt.show()

        # Disconnect VSA from SA hardware
        vsa.write('INITiate:SANalyzer:DISConnect')

    elif analyzer.lower() == 'vma':
        # Create object to control analyzer
        vma = pyarbtools.vsaControl.VMA(saIpAddress)

        """The commands below are sent by default in the VMA constructor, this section is just for reference"""
        # # select and preset OFDM measurement in the vector modulation analyzer mode
        # vma.write("instrument:select vma")
        # vma.write("configure:ofdm")
        # vma.write("configure:ofdm:ndefault")

        # Optional: transfer xml setup file to analzyer
        # Note that this file may already be on the analyzer
        sourcePath = "C:\\Users\\moalliso\\OneDrive - Keysight Technologies\\Documents\\!Keysight\\!Customers\\Amazon\\Kuiper\\Kuiper Wfm Development\\Abishek\\400MHz-cp-ofdm-longer-cp.xml"
        destinationPath = "D:\\Users\\Instrument\\Desktop\\Morgan\\400MHz-cp-ofdm-longer-cp.xml"
        # sourcePath = "C:\\Users\\moalliso\\OneDrive - Keysight Technologies\\Documents\\!Keysight\\!Customers\\Amazon\\Kuiper\\Kuiper Wfm Development\\Abishek\\500MHz-cp-ofdm-longer-cp.xml"
        # destinationPath = "D:\\Users\\Instrument\\Desktop\\Morgan\\500MHz-cp-ofdm-longer-cp.xml"

        vma.send_file_to_analyzer(sourcePath=sourcePath, destinationPath=destinationPath)

        # Recall demod info (this defines EVERYTHING about the OFDM waveform and is REQUIRED for demodulation)
        vma.load_demod_definition(destinationPath)

        # Set analyzer cf
        vma.write(f'SENSe:OFDM:CCARrier:REFerence {cf}')

        # equalizer
        vma.ofdm_equalizer_setup(useData=False, useDCPilot=False, usePilot=True, usePreamble=False)
        
        # tracking
        vma.ofdm_tracking_setup(useData=False, amplitude=False, phase=True, timing=False)

        # path select
        vma.set_uw_path('mpb')

        # preamp
        if cf < 3.6e9:
            vma.set_preamp_band('low')
        else:
            vma.set_preamp_band('full')
        vma.set_preamp_state(False)
        
        # VMA Display settings
        vma.write("sense:ofdm:ccarrier0:evm:report:db on")
        vma.write(f"display:ofdm:window3:x:scale:width {span}")
        vma.write(f"display:ofdm:window3:x:scale:rlevel {cf}")

        # Configure signal generator power levels and optimized attenuator/if gain settings for analyzer
        # These will be used for the power sweep loop example
        sigPowerList = [-20, -10, 0]
        
        # This is for the 400 MHz signal
        attenList = [0, 0, 0]
        ifGainList = [4, -8, -16]

        # This set is for the 500 MHz signal
        # attenList = [0, 0, 6]
        # ifGainList = [-4, -14, -16]

        for p, a, i in zip(sigPowerList, attenList, ifGainList):
            # Set optimal attenuation and IF gain for specific wfm and sig gen output power
            vma.set_attenuation(atten=a)
            vma.set_if_gain(ifGain=i)

            # Set sig gen output power
            vxg.configure(amp=p)
            
            # Acquire data and print results
            results = vma.get_ofdm_results()
            print(f'Signal Power: {p} dBm, Attenuation: {a} dB, IF Gain: {i} dB')
            print(f'RMS EVM: {results["rmsEvm"]:.3} dB')

            vma.err_check()

        vma.acquire_continuous()

    else:
        raise ValueError("Analzyer must be 'vsa' or 'vma'.")


def main():
    vxgIpAddress="192.168.50.22"
    saIpAddress="192.168.50.3"
    full_generate_demod(analyzer='vsa', vxgIpAddress=vxgIpAddress, saIpAddress=saIpAddress)


if __name__ == "__main__":
    main()