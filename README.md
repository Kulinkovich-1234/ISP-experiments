# Physics Laboratory Experiments — Portfolio Showcase

> **⚠️ ACADEMIC INTEGRITY WARNING**
>
> This repository is published for **portfolio and demonstration purposes only**. The code shows the *structure* of physics lab data analysis — data loading, preprocessing, and visualization pipelines — but intentionally **removes core fitting algorithms and calibrated parameters** that would produce final answers.
>
> **Any use of this material for coursework submission at Peking University or any other academic institution constitutes plagiarism and is strictly prohibited.**
>
> The raw experimental data provided is intentionally incomplete/uncalibrated and cannot be used to derive correct results without deriving and implementing the fitting algorithms yourself. If you are a student looking for homework answers, **you will not find them here.**
>
> *— The author*

---

## Overview

This repository contains **6 undergraduate physics laboratory experiments** covering optics, electronics, spectroscopy, and analytical chemistry. Each Lab directory contains Python analysis scripts, supporting data files, and documentation of the experimental setup.

### What's Included

Each experiment demonstrates:
- **Experimental design and data acquisition** workflows
- **Data preprocessing** (loading, cleaning, normalization)
- **Visualization** (matplotlib plotting, interactive widgets)
- **Structural code** for the analysis pipeline

### What's Intentionally Removed

- **Core curve-fitting algorithms** (replaced with `raise NotImplementedError`)
- **Calibrated experimental parameters** (replaced with `None` placeholders)
- **Processed/calibrated CSV data files** (removed; only raw uncalibrated data remains)
- **LaTeX report source and compiled PDFs** (contain complete lab write-ups)

The goal is to show *how* the analysis is structured while requiring anyone who wishes to reproduce the results to derive the physics models themselves.

---

## Lab Contents

### Lab1 — Optical Spectroscopy
- Spectral image extraction from photographs
- RGB channel peak alignment across multiple images
- Interactive alignment tools with manual slider controls
- Files: `fluorescent_lamp_aligning_script.py`, `fluorescent_lamp_peak_aligning.py`, `spectra_detail_viewer.py`

### Lab2 — Lens Focal Length Measurement
- Thin-lens equation linearization
- Image height measurement from photographs
- Files: `fit_focal.py`

### Lab3 — Digital Logic & LabVIEW
- LabVIEW VI files for binary counting and prime number detection
- Files: `PRIME.vi`, `binary_counter.ms14`, `check.py`

### Lab4 — RC Circuits & Temperature Measurement
- RC high-pass filter Bode plot analysis
- NTC thermistor calibration and temperature measurement
- Electromagnet control via DAQ
- Audio waveform generation (music synthesis extras)
- Files: `RC_circuit_fit.py`, `temperature_calibration.py`, `temperature_measure.py`

### Lab5 — LED I-V Characterization
- LED current-voltage curve measurement and fitting
- Shockley diode equation model vs. exponential model
- Files: `LED_UI_fit.py`, `LED_UI_measurement.py`

### Lab6 — Automated Titration (EDTA)
- Syringe pump control via serial
- Photodetector-based endpoint detection
- 3D-printed cuvette holder designs (STL files)
- RC step-response model for titration curve fitting
- Files: `titration.py`, `process_titration.py`, `syringe_control.py`

---

## Repository Structure

```
d:/ISP-experiments/
├── Lab1/            # Optical spectroscopy
├── Lab2/            # Lens focal length
├── Lab3/            # Digital logic
├── Lab4/            # RC circuits & temperature
├── Lab5/            # LED I-V characterization
├── Lab6/            # Automated titration
├── assets/          # Non-code media (images, CAD models, helper scripts)
├── .gitignore
├── LICENSE          # CC BY-NC-SA 4.0
└── README.md
```

---

## License

This work is licensed under the **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License** (CC BY-NC-SA 4.0).

You are free to:
- **Share** — copy and redistribute the material in any medium or format
- **Adapt** — remix, transform, and build upon the material

Under the following terms:
- **Attribution** — You must give appropriate credit
- **NonCommercial** — You may not use the material for commercial purposes
- **ShareAlike** — If you remix, transform, or build upon the material, you must distribute your contributions under the same license

See [LICENSE](./LICENSE) for full details.

---

*Copyright &copy; 2026. Released under CC BY-NC-SA 4.0.*
