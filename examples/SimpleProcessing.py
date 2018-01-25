import numpy as np
import matplotlib.pyplot as plt
from scipy import signal
from scipy.signal import correlate, filtfilt, firwin, freqz
import easygui
from tempfile import TemporaryFile
import os

from ..dgp.lib.eotvos import calc_eotvos
from ..dgp.lib.timesync import find_time_delay, time_Shift_array
from lib.trajectory_ingestor import import_trajectory
from lib.gravity_ingestor import read_at1a

os.getcwd()

MeterGain = 1.0

plt.interactive(True)
# was sept7.dat
path = easygui.fileopenbox()
# meter=read_at1a('tests\january10vant2st.dat')
meter = read_at1a(path)
fields = ['mdy', 'hms', 'lat', 'long', 'ortho_ht', 'ell_ht', 'num_sats', 'pdop']
# was Possept7.txt
path = easygui.fileopenbox()
gpsdata = import_trajectory(path, columns=fields, skiprows=1, timeformat='hms')


def find_nearest(array, value):
    idx = (np.abs(array - value)).argmin()
    return idx


# newindex = meter.index.union(gpsdata.index)
# meter= meter.reindex(newindex)
# gpsdata = gpsdata.reindex(newindex)

if meter.index[0] >= gpsdata.index[0]:
    start = meter.index[0]
else:
    start = gpsdata.index[0]

if meter.index[-1] >= gpsdata.index[-1]:
    end = gpsdata.index[-1]
else:
    end = meter.index[-1]

meter = meter[start: end]
gpsdata = gpsdata[start: end]
Eotvos = calc_eotvos(gpsdata.lat.values, gpsdata.long.values,
                     gpsdata.ell_ht.values, 10)

# filter design for time sync
fs = 10  # sampling frequency
nyq_rate = fs / 2
numtaps = 2001
fc = 0.01  # frequecy stop
Nfc = fc / nyq_rate  # normaliced cutt of frequency
a = 1.0
b = signal.firwin(numtaps, Nfc, window='blackman')
fgv = signal.filtfilt(b, a, meter.gravity)
fet = signal.filtfilt(b, a, Eotvos)
timef = find_time_delay(fet, -fgv, 10)
print('time shift filtered', timef)
#


#  Use this for big lag determination
#  corr = correlate(ref, target)
# lag = len(ref) - 1 - np.argmax(corr)

time = find_time_delay(Eotvos, -meter.gravity, 10)
print('time shift', time)
# time= 0.763     # overwrite here
gravitys = time_Shift_array(meter.gravity, -time, 10)
time = find_time_delay(Eotvos, -gravitys, 10)
print('time shift fixed', time)
Total = MeterGain * gravitys + Eotvos

# select the lines using eotvos no vertical acce
h = np.zeros(len(gpsdata.ell_ht))
Eot_simple = calc_eotvos(gpsdata.lat.values, gpsdata.long.values, h, 10)
plt.figure(figsize=(14, 9))
# plt.figure()
plt.title('Eotvos_simple')
plt.plot(Eot_simple)
plt.show()

# easygui.msgbox('continue')
nlines = int(easygui.enterbox('Select numbe of lines'))
clicks = 2 * nlines

x = plt.ginput(clicks, timeout=100)
print("clicked", x)
np.save('lines', x)

# filter design
fs = 10  # sampling frequency
nyq_rate = fs / 2
numtaps = 2001
fc = 0.008  # frequecy stop
Nfc = fc / nyq_rate  # normaliced cutt of frequency
a = 1.0
b = signal.firwin(numtaps, Nfc, window='blackman')

"""
w, h = freqz(b,worN=8000)
plt.plot((w/np.pi)*nyq_rate, np.absolute(h), linewidth=1)
plt.xlabel('Frequency (Hz)')
plt.ylabel('Gain')
plt.title('Frequency Response')
plt.ylim(-0.1,1.1)
plt.xlim(0,0.1)
plt.grid(True)
"""

fGrav = signal.filtfilt(b, a, Total)
# fGrav=signal.filtfilt(b,a,fGrav1)
flong = signal.filtfilt(b, a, gpsdata.long)
flat = signal.filtfilt(b, a, gpsdata.lat)

# cut the data in lines
# llong = {}
# lgrav = {}
plt.interactive(False)
plt.figure()
plt.title('Corrected Gravity stack')

longmin = 10000
longmax = -10000

for n in range(0, nlines):
    a = int(x[2 * n][0])
    b = int(x[2 * n + 1][0])
    plt.plot(flong[a:b], fGrav[a:b], label=n)
    minl = min(flong[a:b])
    maxl = max(flong[a:b])
    if minl < longmin:
        longmin = minl
    if maxl > longmax:
        longmax = maxl
plt.legend()
plt.show()

# calculate repeats
a = int(x[0][0])
b = int(x[1][0])

longrange = flong[a + 1000:b - 1000]
latrange = flat[a + 100:b - 100]

# longrange=np.linspace(longmin,longmax,len(flong))


# built the lonfitude  to generate the test points

Avg = []
Inter = []
foravgg = []
foravglo = []

plt.figure()

sumg = 0
for l in range(0, nlines):
    a = int(x[2 * l][0])
    b = int(x[2 * l + 1][0])
    lo = flong[a:b]
    la = flat[a:b]
    g = fGrav[a:b]
    Inter = []
    dr = 0.001
    for n in range(0, len(longrange), 10):
        indices = np.where(
            np.logical_and(lo >= longrange[n] - dr, lo <= longrange[n] + dr))
        point = np.array(indices)
        Inter.append(point.item(0))

    # plt.plot(lo[point.item(0)],g[point.item(0)])
    print('number of intersections', len(Inter))
    plt.plot(lo[Inter], g[Inter])
    foravglo.append(lo[Inter])
    foravgg.append(g[Inter])
# find average line
avg = np.sum(foravgg, axis=0)
avg = avg / nlines
plt.plot(lo[Inter], avg, 'r--')
plt.show()

# calculate sigma mean error
meanerror = []
meanabs = 0
plt.figure()
plt.title('Error to to the mean')
for l in range(0, nlines):
    error = foravgg[l] - avg
    meanabs = meanabs + np.mean(np.absolute(error))
    meanerror.append(error)
    plt.plot(error)

meanabserror = meanabs / nlines
print('mean absolute error', meanabserror)

print(np.std(meanerror, axis=1))
stdev = np.std(meanerror, axis=1)
print(np.sum(stdev, axis=0) / nlines)
