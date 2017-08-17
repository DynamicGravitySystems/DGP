import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# import dgp

from dgp.ui import plotting as plots
from dgp.lib import gravity_ingestor as gi

os.chdir('../tests')
df = gi.read_at1m(os.path.abspath('./test_data.csv'))
plt = plots.Plots()
plt.generate_subplots(df.index, df['gravity'], df['pressure'], df['temp'])
# plt.generate_subplots(df.index, df['gravity'])
