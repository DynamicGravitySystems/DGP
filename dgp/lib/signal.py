from scipy.signal import correlate, filtfilt, firwin
import numpy as np

def xcorr(*, ref, target):
    """
    Compute lag between two signals.

    The lag returned is the shift required to align the reference signal with
    the target signal, in units of samples. Therefore, the resolution of this
    method is limited to the sample rate.

    Parameters
    ----------
        ref: array-like
            Reference signal.
        targe: array-like
            Target signal.

    Returns
    -------
    int
    """

    corr = correlate(ref, target)
    lag = len(ref) - 1 - np.argmax(corr)
    return lag

def lp_filter(x, *, Fs, filter_len):
    """
    Low-pass filter

    FIR low-pass filter designed with a Blackman window.

    Parameters
    ----------
        x: array-like
            Array of data to be filtered
        Fs: float or int
            Sample frequency in Hz
        filter_len: float or int
            Filter length in seconds

    Returns
    -------
        ndarray
    """

    # cutoff frequency in Hz
    Fc = 1.0 / filter_len

    # Nyquist frequency
    Ny = Fs / 2.0

    # cutoff frequency in units of the Nyquist frequency
    Wn = Fc / Ny

    # filter order
    N = 2.0 * filter_len * Fs

    # design filter
    taps = firwin(N, Wn, window='blackman', nyq=Ny)

    # apply filter
    # TO DO: Need a heuristic for adjusting padlen according to the signal
    filtered = filtfilt(taps, 1.0, x, padtype='even', padlen=80)

    return filtered
