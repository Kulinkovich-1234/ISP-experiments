# 北京大学整合科学班综合实验课程 · 个人作品集展示（Physics Laboratory Experiments — Portfolio Showcase）

> **⚠️ 学术诚信警告（ACADEMIC INTEGRITY WARNING）**
>
> 本仓库以 **作品集与演示（portfolio and demonstration）** 为目的公开发布。代码展示了实验数据分析的**程序结构**——数据加载、预处理与可视化流程（data loading, preprocessing, and visualization pipelines）——但**刻意移除了核心拟合算法（core fitting algorithms）与标定后的实验参数（calibrated parameters）**，这些是得出最终答案所必需的部分。
>
> 将本仓库的任何内容直接用于北京大学或其他高校的课程作业提交，均构成**抄袭（plagiarism）**，严格禁止。
>
> 所提供的原始实验数据**故意不完整/未经标定（intentionally incomplete/uncalibrated）**，若不自行推导并实现拟合算法，无法得出正确结果。如果你是来找作业答案的同学，**这里没有你想要的答案。**
>
> *— Kulinkovich-1234*

---

📧 **联系方式 / Contact**  
**校内邮箱（PKU Email）：** `jwma25@stu.pku.edu.cn`

---

## 概览（Overview）

本仓库包含 **6 个本科生综合实验**，涵盖光学（optics）、电子学（electronics）、光谱学（spectroscopy）与分析化学（analytical chemistry）。每个 Lab 目录下均包含 Python 分析脚本、辅助数据文件及实验装置说明文档。

### 包含内容（What's Included）

每个实验展示了：
- **实验设计与数据采集流程（experimental design and data acquisition）**
- **数据预处理（data preprocessing）**：读取、清洗、归一化
- **可视化（visualization）**：matplotlib 绘图与交互控件
- **分析管道的结构性代码（structural code）**

### 刻意移除的内容（What's Intentionally Removed）

- **核心曲线拟合算法（core curve-fitting algorithms）** —— 替换为 `raise NotImplementedError`
- **标定后的实验参数（calibrated experimental parameters）** —— 替换为 `None` 占位符
- **处理/标定后的 CSV 数据文件（processed/calibrated CSV data）** —— 已移除，仅保留原始未标定数据
- **LaTeX 报告源码与编译后的 PDF（report source and compiled PDFs）** —— 包含完整的实验报告内容

本仓库旨在展示**分析是如何被结构化的（how the analysis is structured）**，同时要求任何希望复现结果的人必须自行推导数学/物理模型（derive the physics models themselves）。

---

## 实验内容（Lab Contents）

### Lab1 —— 光学光谱（Optical Spectroscopy）
- 从照片中提取光谱图像（spectral image extraction）
- 多张图像间的 RGB 通道峰值对齐（peak alignment across multiple images）
- 带手动滑块控制的交互式对齐工具（interactive alignment tools）
- 关键文件：`fluorescent_lamp_aligning_script.py`、`fluorescent_lamp_peak_aligning.py`、`spectra_detail_viewer.py`

### Lab2 —— 透镜焦距测量（Lens Focal Length Measurement）
- 薄透镜方程的线性化处理（thin-lens equation linearization）
- 从照片中测量像高（image height measurement）
- 关键文件：`fit_focal.py`

### Lab3 —— 数字逻辑与 LabVIEW（Digital Logic & LabVIEW）
- LabVIEW VI 文件实现二进制计数与质数检测（binary counting and prime number detection）
- 关键文件：`PRIME.vi`、`binary_counter.ms14`、`check.py`

### Lab4 —— RC 电路与温度测量（RC Circuits & Temperature Measurement）
- RC 高通滤波器的 Bode 图分析（Bode plot analysis）
- NTC 热敏电阻标定与温度测量（thermistor calibration and temperature measurement）
- 基于 DAQ 的电磁铁控制（electromagnet control via DAQ）
- 音频波形合成（音乐合成拓展）
- 关键文件：`RC_circuit_fit.py`、`temperature_calibration.py`、`temperature_measure.py`

### Lab5 —— LED I-V 特性表征（LED I-V Characterization）
- LED 电流-电压曲线测量与拟合（current-voltage curve measurement and fitting）
- Shockley 二极管方程模型 vs. 指数模型对比
- 关键文件：`LED_UI_fit.py`、`LED_UI_measurement.py`

### Lab6 —— 自动滴定（Automated Titration，EDTA）
- 通过串口控制注射泵（syringe pump control via serial）
- 基于光电探测器的终点检测（photodetector-based endpoint detection）
- 3D 打印比色皿支架设计（STL 文件）
- 滴定曲线的 RC 阶跃响应模型拟合（RC step-response model fitting）
- 关键文件：`titration.py`、`process_titration.py`、`syringe_control.py`

---

## 仓库结构（Repository Structure）

```
d:/ISP-experiments/
├── Lab1/            # 光学光谱（Optical spectroscopy）
├── Lab2/            # 透镜焦距（Lens focal length）
├── Lab3/            # 数字逻辑（Digital logic）
├── Lab4/            # RC 电路与温度（RC circuits & temperature）
├── Lab5/            # LED I-V 特性（LED I-V characterization）
├── Lab6/            # 自动滴定（Automated titration）
├── assets/          # 非代码素材（images, CAD models, helper scripts）
├── .gitignore
├── LICENSE          # CC BY-NC-SA 4.0
└── README.md
```

---

## 许可证（License）

本作品采用 **知识共享署名-非商业性使用-相同方式共享 4.0 国际许可证（Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License，CC BY-NC-SA 4.0）**。

你可以自由地：
- **共享（Share）** —— 以任何媒介或格式复制和再分发本材料
- **演绎（Adapt）** —— 对本材料进行混编、转换和二次创作

但须遵守以下条款：
- **署名（Attribution）** —— 必须给出适当的署名
- **非商业性使用（NonCommercial）** —— 不得将本材料用于商业目的
- **相同方式共享（ShareAlike）** —— 若你对本材料进行混编、转换或二次创作，你必须以相同的许可证分发你的贡献

详见 [LICENSE](./LICENSE) 文件。

---

*版权所有 &copy; 2026. 以 CC BY-NC-SA 4.0 许可证发布。*

# Physics Laboratory Experiments — Portfolio Showcase

> **⚠️ ACADEMIC INTEGRITY WARNING**
>
> This repository is published for **portfolio and demonstration purposes only**. The code shows the *structure* of physics lab data analysis — data loading, preprocessing, and visualization pipelines — but intentionally **removes core fitting algorithms and calibrated parameters** that would produce final answers.
>
> **Any use of this material for coursework submission at Peking University or any other academic institution constitutes plagiarism and is strictly prohibited.**
>
> The raw experimental data provided is intentionally incomplete/uncalibrated and cannot be used to derive correct results without deriving and implementing the fitting algorithms yourself. If you are a student looking for homework answers, **you will not find them here.**
>
> *— Kulinkovich-1234*

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
