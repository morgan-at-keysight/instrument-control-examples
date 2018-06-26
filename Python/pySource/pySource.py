"""
Instrument Control Class for Keysight AWGs
Author: Morgan Allison
Updated: 06/18
Builds instrument specific classes for each AWG. The classes include minimum
waveform length/granularity checks, binary waveform formatting, sequencer
length/granularity checks, sample rate checks, etc. per AWG.
Uses socket_instrument.py for instrument communication.
Python 3.6.4
Tested on M8190A
"""

from socket_instrument import *
# from time import perf_counter


class AwgError(Exception):
    """AWG Exception class"""


class M8190A(SocketInstrument):
    def __init__(self, host, port=5025, timeout=3, reset=False):
        super().__init__(host, port, timeout)
        print(self.instId)
        if reset:
            self.write('*rst')
            self.query('*opc?')
            self.write('abort')
        self.fs = float(self.query('frequency:raster?').strip())
        self.res = self.query('trace1:dwidth?').strip().lower()
        self.func1 = self.query('func1:mode?').strip()
        self.func2 = self.query('func2:mode?').strip()
        self.out1 = self.query('output1:route?').strip()
        self.out2 = self.query('output2:route?').strip()
        self.cf1 = float(self.query('carrier1:freq?').strip().split(',')[0])
        self.cf2 = float(self.query('carrier2:freq?').strip().split(',')[0])
        self.refSource = self.query('roscillator:source?').strip()
        self.refFreq = float(self.query('roscillator:frequency?').strip())

    def sanity_check(self):
        """Prints out initialized values."""
        print('Sample rate:', self.fs)
        print('Resolution:', self.res)
        print(f'Output path 1: {self.out1}, Output path 2: {self.out2}')
        print(f'Carrier 1: {self.cf1} Hz, Carrier 2: {self.cf2}')
        print(f'Function 1: {self.func1}, Function 2: {self.func2}')
        print('Ref source:', self.refSource)
        print('Ref frequency:', self.refFreq)

    def check_wfm(self, wfm):
        """Checks minimum size and granularity and returns waveform with
        appropriate binary formatting based on the chosen DAC resolution.

        See pages 273-274 in Keysight M8190A User's Guide (Edition 13.0, October 2017) for more info."""

        self.check_resolution()

        rl = len(wfm)
        if rl < self.minLen:
            raise AwgError(f'Waveform length: {rl}, must be at least {self.minLen}.')
        if rl % self.gran != 0:
            raise AwgError(f'Waveform must have a granularity of {self.gran}.')

        return np.array(self.binMult * wfm, dtype=np.int16) << self.binShift

    def configure(self, res='wsp', fs=7.2e9, refSrc='axi', refFreq=100e6, out1='dac', out2='dac', func1='arb', func2='arb', cf1=2e9, cf2=2e9):
        """Sets basic configuration for M8190A and populates AWG attributes accordingly."""

        self.write(f'trace1:dwidth {res}')
        self.res = self.query('trace1:dwidth?').strip().lower()

        self.write(f'frequency:raster {fs}')
        self.fs = float(self.query('frequency:raster?').strip())

        self.write(f'output1:route {out1}')
        self.out1 = self.query('output1:route?').strip()

        self.write(f'func1:mode {func1}')
        self.func1 = self.query('func1:mode?').strip()

        self.write(f'carrier1:freq {cf1}')
        self.cf1 = float(self.query('carrier1:freq?').strip().split(',')[0])

        self.write(f'output2:route {out2}')
        self.out2 = self.query('output2:route?').strip()

        self.write(f'func2:mode {func2}')
        self.func2 = self.query('func2:mode?').strip()

        self.write(f'carrier2:freq {cf2}')
        self.cf2 = float(self.query('carrier2:freq?').strip().split(',')[0])

        self.write(f'roscillator:source {refSrc}')
        self.refSrc = self.query('roscillator:source?').strip()

        self.write(f'roscillator:frequency {refFreq}')
        self.refFreq = float(self.query('roscillator:frequency?').strip())

        self.check_resolution()
        self.err_check()

    def set_resolution(self, res='wsp'):
        """Sets and reads resolution based on user input."""
        self.write(f'trace1:dwidth {res}')
        self.res = self.query('trace1:dwidth?').strip().lower()
        self.check_resolution()

    def iq_wfm_combiner(self, i, q):
        """Combines i and q wfms into a single wfm for download to AWG."""
        iq = np.empty(2 * len(i), dtype=np.int16)
        iq[0::2] = i
        iq[1::2] = q
        return iq

    def check_resolution(self):
        """Populates gran, minLen, binMult, & binShift, plus intFactor & idleGran if using DUC."""

        if self.res == 'wpr':
            self.gran = 48
            self.minLen = 240
            self.binMult = 8191
            self.binShift = 2
        elif self.res == 'wsp':
            self.gran = 64
            self.minLen = 320
            self.binMult = 2047
            self.binShift = 4
        elif 'intx' in self.res:
            # Granularity, min length, and binary formatting are the same for all interpolated modes.
            self.gran = 24
            self.minLen = 120
            self.binMult = 16383
            self.binShift = 1
            self.intFactor = int(self.res.split('x')[-1])
            if self.intFactor == 3:
                self.idleGran = 8
            elif self.intFactor == 12:
                self.idleGran = 2
            elif self.intFactor == 24 or self.intFactor == 48:
                self.idleGran = 1
        else:
            raise AwgError('Invalid resolution selected.')

    def download_wfm(self, wfm, ch=1):
        """Defines and downloads a waveform into the segment memory."""
        wfm = self.check_wfm(wfm)
        length = len(wfm)

        segIndex = int(self.query(f'trace{ch}:catalog?').strip().split(',')[-2]) + 1
        self.write(f'trace{ch}:def {segIndex}, {length}')
        self.binblockwrite(f'trace{ch}:data {segIndex}, 0, ', wfm)

    def download_iq_wfm(self, i, q, ch=1):
        """Defines and downloads an iq waveform into the segment memory."""
        i = self.check_wfm(i)
        q = self.check_wfm(q)
        iq = self.iq_wfm_combiner(i, q)
        length = len(iq) / 2

        segIndex = int(self.query(f'trace{ch}:catalog?').strip().split(',')[-2]) + 1
        self.write(f'trace{ch}:def {segIndex}, {length}')
        self.binblockwrite(f'trace{ch}:data {segIndex}, 0, ', iq)


class M8195A(SocketInstrument):
    def __init__(self, host, port=5025, timeout=3, reset=False):
        super().__init__(host, port, timeout)
        print(self.instId)
        if reset:
            self.write('*rst')
            self.query('*opc?')
        self.dacMode = self.query('inst:dacm?').strip()
        self.fs = float(self.query('frequency:raster?').strip())
        self.func = self.query('func:mode?').strip()
        self.refSource = self.query('roscillator:source?').strip()
        self.refFreq = float(self.query('roscillator:frequency?').strip())
        self.gran = 256
        self.minLen = 256
        self.binMult = 127
        self.binShift = 0

    def sanity_check(self):
        """Prints out initialized values."""
        print('Sample rate:', self.fs)
        print('DAC Mode:', self.dacMode)
        print('Function:', self.func)
        print('Ref source:', self.refSource)
        print('Ref frequency:', self.refFreq)

    def check_wfm(self, wfm):
        """Checks minimum size and granularity and returns waveform with
        appropriate binary formatting based on the chosen DAC resolution.

        See pages 273-274 in Keysight M8195A User's Guide (Edition 13.0, October 2017) for more info."""

        rl = len(wfm)
        if rl < self.minLen:
            raise AwgError(f'Waveform length: {rl}, must be at least {self.minLen}.')
        if rl % self.gran != 0:
            raise AwgError(f'Waveform must have a granularity of {self.gran}.')

        return np.array(self.binMult * wfm, dtype=np.int8) << self.binShift

    def configure(self, dacMode='single', fs=64e9, refSrc='axi', refFreq=100e6, func='arb'):
        """Sets basic configuration for M8195A and populates AWG attributes accordingly."""

        self.write(f'inst:dacm {dacMode}')
        self.dacMode = self.query('inst:dacm?').strip().lower()

        self.write(f'frequency:raster {fs}')
        self.fs = float(self.query('frequency:raster?').strip())

        self.write(f'func:mode {func}')
        self.func = self.query('func:mode?').strip()

        self.write(f'roscillator:source {refSrc}')
        self.refSrc = self.query('roscillator:source?').strip()

        self.write(f'roscillator:frequency {refFreq}')
        self.refFreq = float(self.query('roscillator:frequency?').strip())

        self.err_check()

    def download_wfm(self, wfm, ch=1):
        """Defines and downloads a waveform into the segment memory."""
        wfm = self.check_wfm(wfm)
        length = len(wfm)

        segIndex = int(self.query(f'trace{ch}:catalog?').strip().split(',')[-2]) + 1
        self.write(f'trace{ch}:def {segIndex}, {length}')
        self.binblockwrite(f'trace{ch}:data {segIndex}, 0, ', wfm)


def main():
    awg = M8190A('10.112.181.78', port=5025, reset=True)
    awg.set_resolution('intx48')
    awg.sanity_check()
    # wfm = np.sin(np.linspace(0, 2 * np.pi, 2400))
    i = np.ones(awg.minLen, dtype=np.int16)
    q = np.zeros(awg.minLen, dtype=np.int16)
    iq = awg.iq_wfm_combiner(i, q)
    awg.download_wfm(iq, iq=True)
    awg.write('carrier:freq 2e9')
    awg.write('func:mode arb')
    awg.write('trace:select 1')
    awg.write('output1:route ac')
    awg.write('output1:norm on')
    awg.write('init:imm')
    awg.query('*opc?')
    awg.err_check()
    awg.disconnect()


if __name__ == '__main__':
    main()
