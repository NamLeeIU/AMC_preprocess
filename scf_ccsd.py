import numpy as np
import math
import sys
from scipy.fft import fft, fftshift
from scipy import signal


def block_samples(s, window_size, step):
    L = s.shape[-1]
    no = int(np.floor((L - window_size) / step)) + 1
    shape = (no, window_size)
    strides = (s.strides[-1] * step, s.strides[-1])  # size block * window
    return np.lib.stride_tricks.as_strided(s, shape=shape, strides=strides)


def scf_fam(s: np.ndarray, ws: int, step: int=0, padding: bool=True, mtd: int=2) -> np.ndarray:
    '''
    I follow the wiki step by step to write this function:
    https://en.wikipedia.org/wiki/Spectral_correlation_density
    '''
    L = s.shape[-1]
    
    if step == 0:
        step = ws // 4
    
    no = int(np.floor((L - ws) / step)) + 1

    if no & (no - 1) != 0 and padding:
        #print ('lenght not enough! padding zero!!')
        Pe = int(np.floor(int(np.log(no)/np.log(2))))
        P = 2**(Pe+1)
        s = np.concatenate((s, np.zeros((int((P-1)*step+ws)-L), dtype=s.dtype)), axis=-1)

    s = block_samples(s, ws, step)
    P = s.shape[0]
    window = signal.windows.hamming(ws)
    window /= np.sqrt(np.sum(window**2))
    s = fftshift(fft(s * window, axis=-1), axes=(-1))
    omega = np.arange(1, (2-ws)/ws, (2-2*ws)/(ws**2))
    suanzi = np.outer(np.arange(P), omega)
    suanzi = np.exp(-1j*np.pi*step*suanzi)

    s = np.multiply(s, suanzi)
    scf = np.einsum('ij,ik->ijk', np.conjugate(s), s)
    
    if mtd == 0:
        return np.abs(np.average(scf, axis=0))

    elif mtd == 1:
        scf = fftshift(fft(scf, axis=0), axes=0)
        return np.abs(np.average(scf, axis=0))

    elif mtd == 2:
        scf = fftshift(fft(scf, axis=0), axes=0)
        scf = np.abs(scf)
        Sx = np.zeros((ws, 2*P*step), dtype=float)
        Mp = (P*step)//ws//2
        for k in range(ws):
            for l in range(ws):
                i = int((k+l)/2.0)
                a = int(((k-l)/float(ws)+1.)*P*step)
                Sx[i, a-Mp:a+Mp] = scf[(P//2-Mp):(P//2+Mp),k,l]
        return Sx

    
def SCD(s: np.ndarray, N: int, L: int=0, pad: bool=True, algorithm: int=2) -> np.ndarray:
    if type(s).__module__ != np.__name__ or len(s.shape) != 2:
        sys.exit("the data should be 2D numpy array")
    o = []
    for i in s:
        x = scf_fam(i, N, L, pad, algorithm)
        o.append((x - np.amin(x)) / (np.amax(x) - np.amin(x)))
    return np.asarray(o)


def ccsd(s: np.ndarray, ws: int, step: int, sigma: float) -> np.ndarray:
    '''
    I follow the steps listed in this paper:
    https://www.sciencedirect.com/science/article/pii/S0957417416305607
    '''
    s = block_samples(s, ws, step)
    L = s.shape[0]
    s = np.concatenate((s, np.zeros((L, ws), dtype=s.dtype)), axis=-1)
    o = []
    for tau in range(ws):
        x = (1 / sigma*np.sqrt(2*np.pi)) * np.exp(-1 * np.abs(s[:, :ws] - s[:, tau:(tau+ws)])**2 / (2*sigma**2))
        o.append(x)

    o = np.asarray(o)
    M = np.mean(o, axis=(0, 2), keepdims=True)
    V = fftshift(fft((o - M), axis=-1), axes=-1)
    V = np.mean(V, axis=1)
    K = fftshift(fft(V, axis=0), axes=0)
    return np.abs(K)


def CCSD(s, N, L, sigma):
    if type(s).__module__ != np.__name__ or len(s.shape) != 2:
        sys.exit("the data should be 2D numpy array")
    o = []
    for i in s:
        x = ccsd(i, N, L, sigma)
        o.append((x - np.amin(x)) / (np.amax(x) - np.amin(x)))
    return np.asarray(o)
