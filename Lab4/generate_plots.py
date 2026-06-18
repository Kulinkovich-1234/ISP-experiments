import csv
import numpy as np
import matplotlib.pyplot as plt

# Read CSV data
freq, gain_linear, gain_db, phase_deg, h_real, h_imag = [], [], [], [], [], []
with open('rc_circuit_results.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        g = float(row['Gain_Linear'])
        if g > 0:  # use positive gain entries
            freq.append(float(row['Frequency(Hz)']))
            gain_linear.append(g)
            gain_db.append(float(row['Gain_dB']) if row['Gain_dB'] != 'nan' else np.nan)
            phase_deg.append(float(row['Phase_Shift_Deg']))
            h_real.append(float(row['H_Real']))
            h_imag.append(float(row['H_Imag']))

freq = np.array(freq)
gain_linear = np.array(gain_linear)
gain_db = np.array(gain_db)
phase_deg = np.array(phase_deg)
h_real = np.array(h_real)
h_imag = np.array(h_imag)

# ======================
# Figure 1: Bode Plot
# ======================
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)

# Magnitude (dB)
ax1.semilogx(freq, 20 * np.log10(gain_linear), 'bo-', markersize=4, linewidth=1)
ax1.set_ylabel('Gain (dB)', fontsize=12)
ax1.set_title('RC High-Pass Filter Bode Plot (DAQ Automated Measurement)', fontsize=13)
ax1.grid(True, which='both', ls='-', alpha=0.3)
ax1.axhline(y=-3, color='r', linestyle='--', alpha=0.5, label='-3 dB')
ax1.legend()

# Phase
ax2.semilogx(freq, phase_deg, 'ro-', markersize=4, linewidth=1)
ax2.set_xlabel('Frequency (Hz)', fontsize=12)
ax2.set_ylabel('Phase Shift (Degrees)', fontsize=12)
ax2.grid(True, which='both', ls='-', alpha=0.3)

plt.tight_layout()
plt.savefig('images/bode_plot.png', dpi=300, bbox_inches='tight')
plt.close()
print("Bode plot saved to images/bode_plot.png")

# ======================
# Figure 2: Nyquist Plot
# ======================
fig, ax = plt.subplots(figsize=(8, 8))
ax.plot(h_real, h_imag, 'bo-', markersize=5, linewidth=1, label='Measured')
ax.plot(h_real[0], h_imag[0], 'go', markersize=8, label='Start (100 Hz)')
ax.plot(h_real[-1], h_imag[-1], 'ro', markersize=8, label='End (4000 Hz)')
ax.axhline(y=0, color='k', linewidth=0.5)
ax.axvline(x=0, color='k', linewidth=0.5)
ax.set_xlabel('Real Part H_real', fontsize=12)
ax.set_ylabel('Imaginary Part H_imag', fontsize=12)
ax.set_title('Nyquist Plot of RC Circuit Transfer Function', fontsize=13)
ax.grid(True, alpha=0.3)
ax.set_aspect('equal')
ax.legend()

# Annotate some frequency points
for i in range(0, len(freq), max(1, len(freq)//8)):
    if i < len(freq):
        ax.annotate(f'{freq[i]:.0f} Hz', (h_real[i], h_imag[i]),
                    textcoords="offset points", xytext=(5, 5), fontsize=8)

plt.tight_layout()
plt.savefig('images/nyquist_plot.png', dpi=300, bbox_inches='tight')
plt.close()
print("Nyquist plot saved to images/nyquist_plot.png")

# ======================
# Figure 3: Temperature monitoring chart
# ======================
import csv
from datetime import datetime

timestamps = []
temperatures = []
resistances = []

with open('temperature_log.csv', 'r') as f:
    reader = csv.reader(f)
    header = next(reader)
    for row in reader:
        timestamps.append(datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S'))
        temperatures.append(float(row[4]))
        resistances.append(float(row[3]))

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7), sharex=True)

ax1.plot(timestamps, temperatures, 'r-', linewidth=0.8)
ax1.set_ylabel('Temperature (°C)', fontsize=12)
ax1.set_title('Real-Time Temperature Monitoring (NTC Thermistor)', fontsize=13)
ax1.grid(True, linestyle='--', alpha=0.3)

ax2.plot(timestamps, resistances, 'b-', linewidth=0.8)
ax2.set_xlabel('Time', fontsize=12)
ax2.set_ylabel('Resistance (Ω)', fontsize=12)
ax2.grid(True, linestyle='--', alpha=0.3)

plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('images/temperature_monitoring.png', dpi=300, bbox_inches='tight')
plt.close()
print("Temperature plot saved to images/temperature_monitoring.png")

# ======================
# Figure 4: Temperature spike (failure analysis)
# ======================
fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(timestamps, temperatures, 'r-', linewidth=0.8, label='Temperature')
# Highlight the spike region
for i, t in enumerate(temperatures):
    if t < 0:
        ax.plot(timestamps[i], t, 'bo', markersize=6, zorder=5)
ax.set_xlabel('Time', fontsize=12)
ax.set_ylabel('Temperature (°C)', fontsize=12)
ax.set_title('Temperature Anomaly Spike — Contact Failure Analysis', fontsize=13)
ax.grid(True, linestyle='--', alpha=0.3)
ax.legend()

plt.tight_layout()
plt.savefig('images/temp_spike.png', dpi=300, bbox_inches='tight')
plt.close()
print("Temperature spike plot saved to images/temp_spike.png")

print("\nAll plots generated successfully!")
