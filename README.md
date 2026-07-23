<div align="center">

# 🤟 Real-Time Sign Language Recognition & Speech Translation System

**A Deep Learning & Computer Vision System for Non-Invasive Gesture Translation**

[![Python Version](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![TensorFlow](https://img.shields.io/badge/TensorFlow-2.17-FF6F00?style=for-the-badge&logo=tensorflow&logoColor=white)](https://www.tensorflow.org/)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10.21-00979D?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/edge/mediapipe/solutions/guide)
[![Test Accuracy](https://img.shields.io/badge/Test_Accuracy-98.67%25-10B981?style=for-the-badge&logo=keras&logoColor=white)](#-model-evaluation--empirical-results)
[![License](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](LICENSE)

</div>

---

## 📸 System Demonstration

<div align="center">
  <img src="app/static/img/demo_hd_white.gif" alt="Real-Time Sign Language Recognition HD Demo" width="840" style="border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);" />
  <p><em>Figure 1: High-Definition live webcam viewport featuring MediaPipe landmark tracking, predicted gesture hero display, top-3 confidence progress meters, active hand detection gating, and Sign-to-Speech audio synthesis.</em></p>
</div>

---

## 🌟 Executive Overview & Key Highlights

This project presents a **real-time, end-to-end Sign Language Recognition (SLR) and Speech Translation Platform**. By combining **Google MediaPipe 3D Keypoint Estimation** with a **Multi-Layer LSTM Temporal Neural Network**, the system converts spatial hand and pose movements into translated text and spoken audio in real time.

- **⏱️ Sub-30ms Real-Time Latency**: High-speed frame processing executing smoothly at 15+ FPS.
- **🔊 Sign-to-Speech Translation**: Asynchronous `pyttsx3` text-to-speech engine speaks recognized gestures aloud for full accessibility.
- **🚫 Active Hand Detection Gating**: Prevents false predictions when signer arms are resting; displays `[ NO HAND DETECTED ]` during inactivity.
- **🎯 45% Minimum Confidence Threshold**: Filters out ambiguous arm movements to maintain high recognition precision.
- **🖥️ 100% Native Desktop Application (`cv2main.py`)**: Built with Python Tkinter featuring 4 dedicated workspace tabs (Live Translation, Video Recording, Video Import, & Interactive Gallery).

---

## 🏗️ System Architecture & Methodology Flowchart

The data pipeline replaces heavy raw video frames with normalized 3D keypoint vectors, ensuring complete independence from signer background, clothing, or camera distance.

```
┌─────────────────────────┐
│  1. HD Webcam Capture   │  640x480 resolution @ 15 FPS
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ 2. MediaPipe Landmark   │  Extracts 21 Hand Landmarks per hand (X, Y, Z)
│     Extraction          │  + 6 Upper-Body Pose Joints (Shoulders, Elbows, Wrists)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ 3. Sliding Window       │  Aggregates 0.5s time windows (~7-8 frames)
│    Feature Vector       │  Computes 18 statistical features (Mean & Std Dev)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ 4. StandardScaler       │  Normalizes feature dimensions to zero mean & unit variance
│    Normalization        │  (Ensures position & scale invariance across signers)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ 5. LSTM Sequence Model  │  5 Consecutive Feature Windows -> Input Shape (1, 5, 18)
│    Classifier           │  Multi-Layer LSTM (128 -> 64 units) + Softmax Output
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ 6. Desktop GUI & Audio  │  Displays Predicted Sign in Hero Card + Top-3 Bars
│    Speech Output        │  Triggers Pyttsx3 Text-to-Speech Voice Output
└─────────────────────────┘
```

---

## 🧠 LSTM Neural Network Architecture

The classification core consists of a **Sequential Long Short-Term Memory (LSTM)** deep learning model designed for sequential spatial-temporal dynamics:

```
Input Tensor (Shape: 1, 5, 18)
  │
  ├──► LSTM Layer 1 (128 Units, return_sequences=True)
  │      ├──► Dropout (Rate: 0.3)
  │      └──► Batch Normalization
  │
  ├──► LSTM Layer 2 (64 Units, return_sequences=False)
  │      ├──► Dropout (Rate: 0.3)
  │      └──► Batch Normalization
  │
  ├──► Fully Connected Dense Layer (64 Neurons, ReLU Activation)
  │      └──► Dropout (Rate: 0.3)
  │
  └──► Softmax Output Layer (11 Output Classes)
```

---

## 📊 Model Evaluation & Empirical Results

The model was evaluated on a dataset of **3,690 test samples** across 11 target sign language classes:

### 📈 Overall Performance Summary
- **Classification Test Accuracy**: **`98.67%`** (`0.9867`)
- **Categorical Cross-Entropy Loss**: **`0.0459`**
- **Macro Average F1-Score**: **`0.99`**
- **Weighted Average F1-Score**: **`0.99`**

### 📋 Per-Class Performance Benchmark

| Target Sign | Precision | Recall | F1-Score | Evaluation Test Samples |
| :--- | :---: | :---: | :---: | :---: |
| **Afternoon** | `0.99` | `1.00` | `0.99` | 266 |
| **Age** | `0.98` | `0.99` | `0.99` | 387 |
| **Boy** | `1.00` | `1.00` | `1.00` | 290 |
| **Country** | `0.98` | `0.95` | `0.96` | 428 |
| **Day** | `0.99` | `1.00` | `0.99` | 427 |
| **Monday** | `1.00` | `1.00` | `1.00` | 212 |
| **Name** | `0.99` | `0.98` | `0.98` | 401 |
| **Night** | `1.00` | `1.00` | `1.00` | 322 |
| **People** | `1.00` | `1.00` | `1.00` | 422 |
| **Person** | `1.00` | `1.00` | `1.00` | 238 |
| **Time** | `0.93` | `0.96` | `0.95` | 297 |
| **OVERALL AVERAGE** | **`0.99`** | **`0.99`** | **`0.99`** | **3,690** |

---

## 💻 Installation & Quick Start

### 1. Prerequisites
Ensure Python 3.11+ is installed on your system.

### 2. Clone Repository & Setup Virtual Environment
```bash
git clone https://github.com/PiyushTiwari2051/Internship_Project-sign-language-recognition.git
cd Internship_Project-sign-language-recognition

# Create virtual environment
python -m venv Real-Time-SLR

# Activate virtual environment
# Windows:
Real-Time-SLR\Scripts\activate
# Linux/macOS:
source Real-Time-SLR/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Launch Desktop Application
```bash
python cv2main.py
```
*(Alternatively, double-click `run_desktop.bat` on Windows).*

### 4. Launch Flask Web Interface (Alternative)
```bash
python run.py
```

---

## 🖥️ Desktop Application Features

The native desktop application (`cv2main.py`) provides four multi-functional tabs:

1. **🎥 Live Recognition Tab**: Real-time webcam viewport, MediaPipe tracking overlays, hero prediction display, top-3 confidence meters, and voice audio toggle.
2. **📹 Record Dataset Video Tab**: Record custom gesture videos with labels directly from your webcam.
3. **📥 Import Video Tab**: Import existing `.mp4`/`.avi` video files into your local dataset.
4. **🖼️ Dataset Gallery Tab**: Browse, play back with MediaPipe overlays, and manage video records in the SQLite database (`app/sign-language-recognition.sqlite`).

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for more information.

---

## 👤 Author

Developed by **Piyush Tiwari**  
- **Roll No**: `2100270100000` | 7th Semester, CSE-1  
- **Department**: Computer Science & Engineering  
- **Institution**: IMS Engineering College, Ghaziabad, India (2026-27)