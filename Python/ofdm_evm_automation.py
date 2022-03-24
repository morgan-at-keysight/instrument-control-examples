import pyarbtools

def full_generate_demod(analyzer='vma', vxgIpAddress="192.168.50.22", vmaIpAddress="192.168.50.3"):
    """
    This function automates the loading and playback of a waveform created by Keysight N7608C Signal Studio for Custom Modulation
    into an M9384B VXG signal generator and demodulation/analysis on a Keysight X-series signal analyzer with the N9054EM0E
    Vector Modulation Analysis option.
    """
    
    # vxg object creation
    vxg = pyarbtools.instruments.VXG(vxgIpAddress)

    # # waveform import from remote computer
    # wfmPath = "C:\\Temp\\abishek\\480MHz_morgan_ccdf_ContinuousPilot32Filter.csv"
    # wfmID = "kpwfm"
    # with open(wfmPath, newline='\n') as csvFile:
    #     reader = csv.reader(csvFile, delimiter=',')
    #     raw = []
    #     for row in reader:
    #         try:
    #             raw.append(float(row[0]) + 1j * float(row[1]))
    #         except ValueError as e:
    #             print(str(e))
    # wfmData = np.array(raw, dtype=np.complex128)
    
    # waveform import from signal studio on VXG hard drive
    wfmPath = "D:\\Users\\Instrument\\Desktop\\480MHz_morgan_ccdf_ContinuousPilot32Filter.wfm"

    # Waveform setup parameters
    cf = 18e9
    amp = -20
    fs = 960e6
    span = 510e6
    
    # # load waveform from remote computer
    # vxg.download_wfm(wfmData=wfmData, wfmID=wfmID)
    # vxg.play(wfmID=wfmID, ch=1)

    # Load local signal studio waveform file, configure VXG, and begin playback
    vxg.write(f'source:signal:waveform:select "{wfmPath}"')
    vxg.configure(cf1=cf, amp1=amp, fs1=fs, arbState=1, rfState=1, modState=1)

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
        # vsa object creation
        vsaIpAddress = "127.0.0.1"
        hw = "badger"
        # hw = "Analyzer1"
        vsa = pyarbtools.vsaControl.VSA(vsaIpAddress, port=5026, vsaHardware=hw)
        
        # vsa setup
        amplifier = 0 # 0=none, 1=preamp, 2=LNA, 3=LNA+preamp
        ifGain = 4
        atten = 0

        # setx file
        setxPath = "C:\\Users\\moalliso\\OneDrive - Keysight Technologies\\Documents\\!Keysight\\!Customers\\Amazon\\Kuiper\\Kuiper Wfm Development\\Weidong\\morgan_ccdf_ContinuousPilot32Filter.setx"
        vsa.custom_ofdm_format_setup(setupFile=setxPath)
        vsa.query("*opc?")
        vsa.set_data_source(fromHardware=True)
        vsa.set_cf(cf=cf)
        vsa.set_amplifier(amplifier)
        vsa.set_if_gain(ifGain)
        vsa.set_attenuation(atten)

        # equalizer and tracking setup
        vsa.custom_ofdm_equalizer_setup(useData=False, useDCPilot=False, usePilot=True, usePreamble=True)
        vsa.custom_ofdm_tracking_setup(useData=False, amplitude=False, phase=True, timing=False)

        vsa.acquire_single()
    elif analyzer.lower() == 'vma':
        # Create object to control analyzer
        vma = pyarbtools.vsaControl.VMA(vmaIpAddress)

        """The commands below are sent by default in the VMA constructor, this section is just for reference"""
        # # select and preset OFDM measurement in the vector modulation analyzer mode
        # vma.write("instrument:select vma")
        # vma.write("configure:ofdm")
        # vma.write("configure:ofdm:ndefault")

        # Optional: transfer xml setup file to analzyer
        # Note that this file may already be on the analyzer
        sourcePath = "C:\\Temp\\abishek\\480MHz_morgan_ccdf_ContinuousPilot32Filter.xml"
        destinationPath = "C:\\temp\\480MHz_morgan_ccdf_ContinuousPilot32Filter.xml"

        vma.send_file_to_analyzer(sourcePath=sourcePath, destinationPath=destinationPath)

        # Recall demod info (this defines EVERYTHING about the OFDM waveform and is REQUIRED for demodulation)
        vma.load_demod_definition(destinationPath)

        # Set analyzer cf
        vma.write(f'SENSe:OFDM:CCARrier:REFerence {cf}')

        # equalizer
        vma.ofdm_equalizer_setup(useData=False, useDCPilot=False, usePilot=True, usePreamble=True)
        
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
        attenList = [0, 0, 6]
        ifGainList = [12, 3, 0]

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
    vmaIpAddress="192.168.50.3"
    full_generate_demod(analyzer='vma', vxgIpAddress=vxgIpAddress, vmaIpAddress=vmaIpAddress)


if __name__ == "__main__":
    main()