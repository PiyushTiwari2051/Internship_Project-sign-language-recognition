#!/usr/bin/env python3
"""
Real-Time Sign Language Recognition, Translation & Dataset Management System
Native Python Tkinter Desktop Application
"""

import os
import sys
import json
import joblib
import shutil
import warnings
import threading
import time
from datetime import datetime
from collections import deque

import cv2
import numpy as np
from PIL import Image, ImageTk

import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import mediapipe as mp
import keras
from keras.models import load_model

# Audio Speech Engine
try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

warnings.filterwarnings("ignore")

DB_PATH = os.path.join("app", "sign-language-recognition.sqlite")
VIDEO_DIR = os.path.join("app", "videos")
os.makedirs(VIDEO_DIR, exist_ok=True)


def init_sqlite():
    """Ensure SQLite tables exist"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS video (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        path TEXT UNIQUE NOT NULL,
        label TEXT NOT NULL,
        duration REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()


class SignLanguageDesktopApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Real-Time Sign Language Recognition & Dataset Management System")
        self.root.geometry("1200x780")
        self.root.minsize(1050, 700)

        # Standard Desktop Theme
        self.bg_color = "#f4f6f9"
        self.panel_bg = "#ffffff"
        self.text_color = "#212529"
        self.root.configure(bg=self.bg_color)

        init_sqlite()

        # Recognition State Variables
        self.cam_id = 0
        self.cap = None
        self.is_running = False
        self.rec_thread = None

        # Recording State Variables
        self.is_recording = False
        self.rec_cap = None
        self.video_writer = None
        self.rec_label_var = tk.StringVar(value="hello")
        self.rec_file_path = ""

        # TTS State
        self.tts_enabled = tk.BooleanVar(value=True)
        self.last_spoken_label = ""
        self.last_spoken_time = 0

        # Feature Parameters
        self.fps = 15
        self.window_sec = 0.5
        self.window_size = int(self.fps * self.window_sec)
        self.sequence_length = 5

        self.frame_buffer = deque(maxlen=self.window_size)
        self.feature_buffer = deque(maxlen=self.sequence_length)

        self.finger_tips = [4, 8, 12, 16, 20]
        self.pose_joints = [11, 12, 13, 14, 15, 16]

        # Load ML Assets
        self.load_recognition_assets()

        # Build GUI
        self.build_ui()

        # Close Event
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def load_recognition_assets(self):
        """Load Keras LSTM model, Scaler, and Label Encoder"""
        try:
            model_path = "app/model/sign_language_recognition.keras"
            scaler_path = "app/model/scaler.pkl"
            label_encoder_path = "app/model/label_encoder.pkl"
            feature_order_path = "app/model/feature_order.json"

            custom_objs = {
                'Orthogonal': keras.initializers.Orthogonal,
                'GlorotUniform': keras.initializers.GlorotUniform,
                'Zeros': keras.initializers.Zeros,
                'Ones': keras.initializers.Ones,
            }
            self.model = load_model(model_path, custom_objects=custom_objs)
            self.scaler = joblib.load(scaler_path)
            self.label_encoder = joblib.load(label_encoder_path)
            self.vocabulary = list(self.label_encoder.classes_)

            with open(feature_order_path, "r") as f:
                self.feature_order = json.load(f)

            self.mp_hands = mp.solutions.hands
            self.hands = self.mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=2,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )
            self.mp_pose = mp.solutions.pose
            self.pose = self.mp_pose.Pose(
                static_image_mode=False,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )
            self.mp_drawing = mp.solutions.drawing_utils
            self.assets_loaded = True
        except Exception as e:
            self.assets_loaded = False
            self.vocabulary = []
            messagebox.showerror("Asset Load Warning", f"Could not load ML assets:\n{e}")

    def build_ui(self):
        """Construct multi-tab native Tkinter desktop interface"""
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background=self.bg_color)
        style.configure('TNotebook', background=self.bg_color, borderwidth=0)
        style.configure('TNotebook.Tab', font=('Segoe UI', 10, 'bold'), padding=[16, 8])

        # Header Title Banner
        header = tk.Frame(self.root, bg=self.panel_bg, bd=1, relief="solid")
        header.pack(fill="x", padx=15, pady=(15, 10))

        title_inner = tk.Frame(header, bg=self.panel_bg, padx=15, pady=10)
        title_inner.pack(fill="x")

        tk.Label(title_inner, text="Real-Time Sign Language Recognition & Dataset Platform", font=('Segoe UI', 16, 'bold'), bg=self.panel_bg, fg="#1e293b").pack(anchor="w")
        tk.Label(title_inner, text="Live Recognition, Gesture Recording, Dataset Video Import & Interactive Video Gallery", font=('Segoe UI', 9), bg=self.panel_bg, fg="#64748b").pack(anchor="w")

        # Notebook Navigation Tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        # Tab 1: Live Recognition
        self.tab_recognition = tk.Frame(self.notebook, bg=self.bg_color)
        self.notebook.add(self.tab_recognition, text=" 🎥 Live Recognition ")

        # Tab 2: Record Gesture Video
        self.tab_record = tk.Frame(self.notebook, bg=self.bg_color)
        self.notebook.add(self.tab_record, text=" 📹 Record Dataset Video ")

        # Tab 3: Import Video
        self.tab_import = tk.Frame(self.notebook, bg=self.bg_color)
        self.notebook.add(self.tab_import, text=" 📥 Import Video ")

        # Tab 4: Dataset Gallery
        self.tab_gallery = tk.Frame(self.notebook, bg=self.bg_color)
        self.notebook.add(self.tab_gallery, text=" 🖼️ Dataset Gallery ")

        # Build each tab view
        self.build_recognition_tab()
        self.build_record_tab()
        self.build_import_tab()
        self.build_gallery_tab()

        # Bottom Status Bar
        status_bar = tk.Frame(self.root, bg="#e2e8f0", height=26, bd=1, relief="solid")
        status_bar.pack(fill="x", side="bottom")

        self.lbl_status = tk.Label(status_bar, text="Status: Ready", font=('Segoe UI', 9), bg="#e2e8f0", fg="#334155", anchor="w", padx=10)
        self.lbl_status.pack(fill="x", side="left")

    def set_status(self, msg):
        self.lbl_status.config(text=f"Status: {msg}")

    # ==========================================
    # TAB 1: LIVE RECOGNITION & TRANSLATION
    # ==========================================
    def build_recognition_tab(self):
        # Toolbar Controls
        toolbar = tk.Frame(self.tab_recognition, bg=self.panel_bg, bd=1, relief="solid")
        toolbar.pack(fill="x", pady=(10, 10))

        tool_inner = tk.Frame(toolbar, bg=self.panel_bg, padx=12, pady=8)
        tool_inner.pack(fill="x")

        self.btn_start = tk.Button(tool_inner, text="▶ Start Camera", command=self.start_camera, font=('Segoe UI', 10, 'bold'), bg="#10b981", fg="#ffffff", padx=12, pady=4, bd=0, cursor="hand2")
        self.btn_start.pack(side="left", padx=(0, 8))

        self.btn_stop = tk.Button(tool_inner, text="⏹ Stop Camera", command=self.stop_camera, font=('Segoe UI', 10, 'bold'), bg="#ef4444", fg="#ffffff", padx=12, pady=4, bd=0, state="disabled", cursor="hand2")
        self.btn_stop.pack(side="left", padx=4)

        tk.Label(tool_inner, text="Camera:", font=('Segoe UI', 10), bg=self.panel_bg).pack(side="left", padx=(15, 4))
        self.cam_combo = ttk.Combobox(tool_inner, values=["Camera 0 (Default)", "Camera 1", "Camera 2"], state="readonly", width=16)
        self.cam_combo.current(0)
        self.cam_combo.pack(side="left", padx=4)

        chk_tts = tk.Checkbutton(tool_inner, text="🔊 Voice Audio Output", variable=self.tts_enabled, font=('Segoe UI', 10), bg=self.panel_bg)
        chk_tts.pack(side="left", padx=15)

        self.lbl_cam_status = tk.Label(tool_inner, text="● Disconnected", font=('Segoe UI', 10, 'bold'), bg=self.panel_bg, fg="#64748b")
        self.lbl_cam_status.pack(side="right", padx=10)

        # Main Split Frame
        split_frame = tk.Frame(self.tab_recognition, bg=self.bg_color)
        split_frame.pack(fill="both", expand=True)

        # Left Column: Video Viewport
        left_frame = tk.Frame(split_frame, bg=self.panel_bg, bd=1, relief="solid")
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        tk.Label(left_frame, text="Live Camera & Tracking Viewport", font=('Segoe UI', 10, 'bold'), bg="#f8fafc", fg="#334155", anchor="w", padx=10, pady=6, bd=1, relief="solid").pack(fill="x")

        self.video_canvas = tk.Canvas(left_frame, bg="#0f172a", highlightthickness=0)
        self.video_canvas.pack(fill="both", expand=True, padx=8, pady=8)
        self.video_canvas.create_text(300, 220, text="Click 'Start Camera' to launch translation", fill="#94a3b8", font=('Segoe UI', 12, 'bold'))

        # Right Column: Prediction Metrics
        right_frame = tk.Frame(split_frame, bg=self.panel_bg, width=380, bd=1, relief="solid")
        right_frame.pack(side="right", fill="both", expand=False)
        right_frame.pack_propagate(False)

        tk.Label(right_frame, text="Recognition Predictions", font=('Segoe UI', 10, 'bold'), bg="#f8fafc", fg="#334155", anchor="w", padx=10, pady=6, bd=1, relief="solid").pack(fill="x")

        pred_content = tk.Frame(right_frame, bg=self.panel_bg, padx=12, pady=12)
        pred_content.pack(fill="both", expand=True)

        tk.Label(pred_content, text="PREDICTED GESTURE", font=('Segoe UI', 8, 'bold'), bg=self.panel_bg, fg="#64748b").pack(anchor="w")

        self.hero_box = tk.Frame(pred_content, bg="#e0f2fe", bd=1, relief="solid", height=85)
        self.hero_box.pack(fill="x", pady=(2, 12))
        self.hero_box.pack_propagate(False)

        self.lbl_predicted_sign = tk.Label(self.hero_box, text="[ READY ]", font=('Segoe UI', 20, 'bold'), bg="#e0f2fe", fg="#0284c7")
        self.lbl_predicted_sign.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(pred_content, text="TOP 3 CONFIDENCE PROBABILITIES", font=('Segoe UI', 8, 'bold'), bg=self.panel_bg, fg="#64748b").pack(anchor="w", pady=(0, 4))

        self.top3_widgets = []
        for i in range(3):
            item_frame = tk.Frame(pred_content, bg="#f8fafc", bd=1, relief="solid", padx=8, pady=5)
            item_frame.pack(fill="x", pady=2)

            top_row = tk.Frame(item_frame, bg="#f8fafc")
            top_row.pack(fill="x", pady=(0, 2))

            lbl_name = tk.Label(top_row, text=f"{i+1}. -", font=('Segoe UI', 9, 'bold'), bg="#f8fafc", fg="#1e293b")
            lbl_name.pack(side="left")

            lbl_conf = tk.Label(top_row, text="0.0%", font=('Segoe UI', 9, 'bold'), bg="#f8fafc", fg="#0284c7")
            lbl_conf.pack(side="right")

            pbar = ttk.Progressbar(item_frame, length=100, mode='determinate')
            pbar.pack(fill="x")

            self.top3_widgets.append({'name': lbl_name, 'conf': lbl_conf, 'bar': pbar})

        vocab_frame = tk.Frame(pred_content, bg="#f8fafc", bd=1, relief="solid", padx=8, pady=6)
        vocab_frame.pack(fill="x", pady=(10, 0))

        tk.Label(vocab_frame, text="VOCABULARY (11 SIGNS):", font=('Segoe UI', 8, 'bold'), bg="#f8fafc", fg="#475569").pack(anchor="w")
        v_str = ", ".join([v.capitalize() for v in self.vocabulary]) if self.vocabulary else "N/A"
        tk.Label(vocab_frame, text=v_str, font=('Segoe UI', 8), bg="#f8fafc", fg="#334155", wraplength=340, justify="left").pack(anchor="w")

        info_frame = tk.Frame(pred_content, bg="#f1f5f9", bd=1, relief="solid", padx=8, pady=6)
        info_frame.pack(fill="x", side="bottom")

        tk.Label(info_frame, text="ACCURACY & METRICS", font=('Segoe UI', 8, 'bold'), bg="#f1f5f9", fg="#475569").pack(anchor="w")
        tk.Label(info_frame, text="• Test Accuracy: 98.67% | F1: 0.99", font=('Segoe UI', 8, 'bold'), bg="#f1f5f9", fg="#059669").pack(anchor="w")

    def start_camera(self):
        if self.is_running:
            return
        self.is_running = True
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.lbl_cam_status.config(text="● Camera Active", fg="#10b981")
        self.set_status("Starting camera stream...")

        self.thread = threading.Thread(target=self.video_loop, daemon=True)
        self.thread.start()

    def stop_camera(self):
        self.is_running = False
        if self.cap:
            self.cap.release()
            self.cap = None

        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.lbl_cam_status.config(text="● Disconnected", fg="#64748b")
        self.set_status("Camera stopped")
        self.lbl_predicted_sign.config(text="[ Stopped ]", fg="#64748b")
        self.reset_top3_display()

    def reset_top3_display(self):
        for i, item in enumerate(self.top3_widgets):
            item['name'].config(text=f"{i+1}. -")
            item['conf'].config(text="0.0%")
            item['bar']['value'] = 0

    def speak_gesture(self, text):
        if not self.tts_enabled.get() or not TTS_AVAILABLE:
            return
        curr_time = time.time()
        if text == self.last_spoken_label and (curr_time - self.last_spoken_time) < 2.5:
            return

        self.last_spoken_label = text
        self.last_spoken_time = curr_time

        def tts_task(phrase):
            try:
                engine = pyttsx3.init()
                engine.setProperty('rate', 150)
                engine.say(phrase)
                engine.runAndWait()
            except Exception:
                pass

        threading.Thread(target=tts_task, args=(text,), daemon=True).start()

    def extract_landmarks_from_frame(self, frame):
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        hands_results = self.hands.process(frame_rgb)
        pose_results = self.pose.process(frame_rgb)

        landmarks = {"hand_0": [], "hand_1": [], "pose": []}

        if hands_results.multi_hand_landmarks:
            for hand_idx, hand_landmarks in enumerate(hands_results.multi_hand_landmarks):
                if hand_idx > 1:
                    break
                for lm_idx in self.finger_tips:
                    lm = hand_landmarks.landmark[lm_idx]
                    landmarks[f"hand_{hand_idx}"].append({"x": lm.x, "y": lm.y, "z": lm.z})

        if pose_results.pose_landmarks:
            for idx in self.pose_joints:
                lm = pose_results.pose_landmarks.landmark[idx]
                landmarks["pose"].append({"x": lm.x, "y": lm.y, "z": lm.z})

        return landmarks, hands_results, pose_results

    def extract_window_features(self, window_landmarks):
        features = {name: 0.0 for name in self.feature_order}

        pose_coords = {"x": [], "y": [], "z": []}
        for frame_landmarks in window_landmarks:
            for lm in frame_landmarks["pose"]:
                pose_coords["x"].append(lm["x"])
                pose_coords["y"].append(lm["y"])
                pose_coords["z"].append(lm["z"])

        for axis in ["x", "y", "z"]:
            if pose_coords[axis]:
                features[f"joints_{axis}_mean"] = float(np.mean(pose_coords[axis]))
                features[f"joints_{axis}_std"] = float(np.std(pose_coords[axis]))

        for hand_idx, feature_prefix in [(0, "left"), (1, "right")]:
            hand_coords = {"x": [], "y": [], "z": []}
            for frame_landmarks in window_landmarks:
                for lm in frame_landmarks[f"hand_{hand_idx}"]:
                    hand_coords["x"].append(lm["x"])
                    hand_coords["y"].append(lm["y"])
                    hand_coords["z"].append(lm["z"])

            for axis in ["x", "y", "z"]:
                if hand_coords[axis]:
                    features[f"{feature_prefix}_tips_{axis}_mean"] = float(np.mean(hand_coords[axis]))
                    features[f"{feature_prefix}_tips_{axis}_std"] = float(np.std(hand_coords[axis]))

        ordered_features = [features[name] for name in self.feature_order]
        return np.array(ordered_features)

    def predict(self):
        if len(self.feature_buffer) < self.sequence_length:
            return None, None

        # Check if hands are present in recent frame buffer
        has_hands = any(len(lm["hand_0"]) > 0 or len(lm["hand_1"]) > 0 for lm in self.frame_buffer)
        if not has_hands:
            return "NO HAND DETECTED", []

        X = np.array(list(self.feature_buffer)).reshape(1, self.sequence_length, -1)
        X_reshaped = X.reshape(X.shape[1], -1)
        X_scaled = self.scaler.transform(X_reshaped)
        X = X_scaled.reshape(1, X.shape[1], -1)

        predictions = self.model.predict(X, verbose=0)[0]
        top3_indices = np.argsort(predictions)[-3:][::-1]
        top3_labels = self.label_encoder.inverse_transform(top3_indices)
        top3_confidences = predictions[top3_indices]

        # Require at least 45% confidence to display prediction
        if top3_confidences[0] * 100 < 45.0:
            return "UNCERTAIN GESTURE", []

        return top3_labels[0], list(zip(top3_labels, top3_confidences * 100))

    def draw_landmarks(self, frame, hands_results, pose_results):
        if hands_results.multi_hand_landmarks:
            for hand_landmarks in hands_results.multi_hand_landmarks:
                self.mp_drawing.draw_landmarks(
                    frame,
                    hand_landmarks,
                    self.mp_hands.HAND_CONNECTIONS,
                    self.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                    self.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2),
                )

        if pose_results.pose_landmarks:
            for idx in self.pose_joints:
                lm = pose_results.pose_landmarks.landmark[idx]
                h, w = frame.shape[:2]
                cx, cy = int(lm.x * w), int(lm.y * h)
                cv2.circle(frame, (cx, cy), 5, (255, 0, 0), -1)

        return frame

    def video_loop(self):
        idx = self.cam_combo.current()
        for cam_idx in [idx, 0, 1, 2]:
            self.cap = cv2.VideoCapture(cam_idx)
            if self.cap.isOpened():
                break
        else:
            self.root.after(0, lambda: messagebox.showerror("Camera Error", "Could not open webcam device."))
            self.root.after(0, self.stop_camera)
            return

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        self.frame_buffer.clear()
        self.feature_buffer.clear()

        self.root.after(0, lambda: self.set_status("Webcam & MediaPipe translation loop active"))

        while self.is_running and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                break

            landmarks, hands_results, pose_results = self.extract_landmarks_from_frame(frame)
            self.frame_buffer.append(landmarks)

            if len(self.frame_buffer) == self.window_size:
                window_features = self.extract_window_features(self.frame_buffer)
                self.feature_buffer.append(window_features)

            pred_label, top3 = self.predict()

            if pred_label and pred_label not in ["NO HAND DETECTED", "UNCERTAIN GESTURE"] and top3 and top3[0][1] >= 60.0:
                self.speak_gesture(pred_label)

            frame_annotated = self.draw_landmarks(frame.copy(), hands_results, pose_results)

            cv2_img = cv2.cvtColor(frame_annotated, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(cv2_img)

            canvas_w = self.video_canvas.winfo_width()
            canvas_h = self.video_canvas.winfo_height()
            if canvas_w > 10 and canvas_h > 10:
                img = img.resize((canvas_w, canvas_h), Image.Resampling.LANCZOS)

            img_tk = ImageTk.PhotoImage(image=img)

            self.root.after(0, self.update_ui_frame, img_tk, pred_label, top3)
            time.sleep(0.03)

    def update_ui_frame(self, img_tk, pred_label, top3):
        if not self.is_running:
            return

        self.video_canvas.image_tk = img_tk
        self.video_canvas.create_image(0, 0, image=img_tk, anchor="nw")

        if pred_label == "NO HAND DETECTED":
            self.lbl_predicted_sign.config(text="[ NO HAND DETECTED ]", fg="#64748b")
            self.reset_top3_display()
        elif pred_label == "UNCERTAIN GESTURE":
            self.lbl_predicted_sign.config(text="[ UNCERTAIN GESTURE ]", fg="#d97706")
            self.reset_top3_display()
        elif pred_label:
            self.lbl_predicted_sign.config(text=str(pred_label).upper(), fg="#0284c7")
        else:
            self.lbl_predicted_sign.config(text="[ Collecting Frames... ]", fg="#64748b")

        if top3 and pred_label not in ["NO HAND DETECTED", "UNCERTAIN GESTURE"]:
            for i, (lbl, conf) in enumerate(top3[:3]):
                item = self.top3_widgets[i]
                item['name'].config(text=f"{i+1}. {lbl}")
                item['conf'].config(text=f"{conf:.1f}%")
                item['bar']['value'] = min(100, max(0, conf))
        else:
            self.reset_top3_display()

    # ==========================================
    # TAB 2: RECORD DATASET GESTURE VIDEO
    # ==========================================
    def build_record_tab(self):
        container = tk.Frame(self.tab_record, bg=self.panel_bg, bd=1, relief="solid")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # Control panel
        control_panel = tk.Frame(container, bg="#f8fafc", bd=1, relief="solid", padx=15, pady=10)
        control_panel.pack(fill="x", side="top")

        tk.Label(control_panel, text="Gesture Label Name:", font=('Segoe UI', 10, 'bold'), bg="#f8fafc").pack(side="left", padx=(0, 8))
        entry_label = ttk.Entry(control_panel, textvariable=self.rec_label_var, width=20, font=('Segoe UI', 10))
        entry_label.pack(side="left", padx=5)

        self.btn_rec_start = tk.Button(control_panel, text="🔴 Start Recording", command=self.start_recording, font=('Segoe UI', 10, 'bold'), bg="#ef4444", fg="#ffffff", padx=12, pady=4, bd=0, cursor="hand2")
        self.btn_rec_start.pack(side="left", padx=(20, 5))

        self.btn_rec_stop = tk.Button(control_panel, text="⏹ Stop & Save Video", command=self.stop_recording, font=('Segoe UI', 10, 'bold'), bg="#3b82f6", fg="#ffffff", padx=12, pady=4, bd=0, state="disabled", cursor="hand2")
        self.btn_rec_stop.pack(side="left", padx=5)

        self.lbl_rec_status = tk.Label(control_panel, text="● Idle", font=('Segoe UI', 10, 'bold'), bg="#f8fafc", fg="#64748b")
        self.lbl_rec_status.pack(side="right", padx=10)

        # Preview Canvas
        self.rec_canvas = tk.Canvas(container, bg="#0f172a", highlightthickness=0)
        self.rec_canvas.pack(fill="both", expand=True, padx=15, pady=15)
        self.rec_canvas.create_text(400, 250, text="Enter a label name and click 'Start Recording'", fill="#94a3b8", font=('Segoe UI', 12, 'bold'))

    def start_recording(self):
        label = self.rec_label_var.get().strip().lower()
        if not label:
            messagebox.showwarning("Input Required", "Please enter a gesture label name.")
            return

        label_dir = os.path.join(VIDEO_DIR, label)
        os.makedirs(label_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.rec_file_path = os.path.join(label_dir, f"{timestamp}.avi")

        self.is_recording = True
        self.btn_rec_start.config(state="disabled")
        self.btn_rec_stop.config(state="normal")
        self.lbl_rec_status.config(text="🔴 RECORDING...", fg="#ef4444")
        self.set_status(f"Recording video for sign label '{label}'...")

        threading.Thread(target=self.recording_loop, daemon=True).start()

    def recording_loop(self):
        self.rec_cap = cv2.VideoCapture(0)
        self.rec_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.rec_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        self.video_writer = cv2.VideoWriter(self.rec_file_path, fourcc, 15.0, (640, 480))

        while self.is_recording and self.rec_cap and self.rec_cap.isOpened():
            ret, frame = self.rec_cap.read()
            if not ret:
                break

            self.video_writer.write(frame)

            # Draw "RECORDING" indicator on preview
            cv2.circle(frame, (30, 30), 12, (0, 0, 255), -1)
            cv2.putText(frame, "REC", (50, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            cv2_img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(cv2_img)

            cw = self.rec_canvas.winfo_width()
            ch = self.rec_canvas.winfo_height()
            if cw > 10 and ch > 10:
                img = img.resize((cw, ch), Image.Resampling.LANCZOS)

            img_tk = ImageTk.PhotoImage(image=img)

            self.root.after(0, self.update_rec_canvas, img_tk)
            time.sleep(0.03)

        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None

        if self.rec_cap:
            self.rec_cap.release()
            self.rec_cap = None

    def update_rec_canvas(self, img_tk):
        if not self.is_recording:
            return
        self.rec_canvas.image_tk = img_tk
        self.rec_canvas.create_image(0, 0, image=img_tk, anchor="nw")

    def stop_recording(self):
        self.is_recording = False
        self.btn_rec_start.config(state="normal")
        self.btn_rec_stop.config(state="disabled")
        self.lbl_rec_status.config(text="● Saved", fg="#10b981")

        label = self.rec_label_var.get().strip().lower()

        # Save to SQLite
        if os.path.exists(self.rec_file_path):
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("INSERT INTO video (path, label, duration) VALUES (?, ?, ?)", (self.rec_file_path, label, 3.0))
            conn.commit()
            conn.close()

            messagebox.showinfo("Video Saved", f"Gesture video successfully saved to dataset!\nPath: {self.rec_file_path}")
            self.set_status(f"Saved gesture '{label}' to database.")
            self.refresh_gallery()

    # ==========================================
    # TAB 3: IMPORT EXTERNAL VIDEO
    # ==========================================
    def build_import_tab(self):
        card = tk.Frame(self.tab_import, bg=self.panel_bg, bd=1, relief="solid", padx=30, pady=30)
        card.pack(fill="both", expand=True, padx=50, pady=40)

        tk.Label(card, text="Import External Video to Dataset", font=('Segoe UI', 14, 'bold'), bg=self.panel_bg, fg="#1e293b").pack(anchor="w", pady=(0, 15))

        # Select file row
        row1 = tk.Frame(card, bg=self.panel_bg)
        row1.pack(fill="x", pady=10)

        tk.Label(row1, text="Select Video File:", font=('Segoe UI', 10, 'bold'), bg=self.panel_bg, width=16, anchor="w").pack(side="left")
        self.import_path_var = tk.StringVar()
        entry_path = ttk.Entry(row1, textvariable=self.import_path_var, font=('Segoe UI', 10))
        entry_path.pack(side="left", fill="x", expand=True, padx=8)

        btn_browse = tk.Button(row1, text="Browse...", command=self.browse_import_file, font=('Segoe UI', 9, 'bold'), bg="#e2e8f0", padx=12, pady=3)
        btn_browse.pack(side="right")

        # Label row
        row2 = tk.Frame(card, bg=self.panel_bg)
        row2.pack(fill="x", pady=10)

        tk.Label(row2, text="Gesture Label Name:", font=('Segoe UI', 10, 'bold'), bg=self.panel_bg, width=16, anchor="w").pack(side="left")
        self.import_label_var = tk.StringVar()
        entry_imp_label = ttk.Entry(row2, textvariable=self.import_label_var, font=('Segoe UI', 10))
        entry_imp_label.pack(side="left", fill="x", expand=True, padx=8)

        # Import Action Button
        btn_import_action = tk.Button(card, text="📥 Import Video to Dataset", command=self.execute_import, font=('Segoe UI', 11, 'bold'), bg="#10b981", fg="#ffffff", padx=20, pady=8, bd=0, cursor="hand2")
        btn_import_action.pack(anchor="w", pady=25)

        self.lbl_import_msg = tk.Label(card, text="", font=('Segoe UI', 10), bg=self.panel_bg, fg="#059669")
        self.lbl_import_msg.pack(anchor="w")

    def browse_import_file(self):
        file_path = filedialog.askopenfilename(
            title="Select Sign Video File",
            filetypes=[("Video Files", "*.mp4 *.avi *.webm *.mov *.mkv"), ("All Files", "*.*")]
        )
        if file_path:
            self.import_path_var.set(file_path)

    def execute_import(self):
        src_path = self.import_path_var.get().strip()
        label = self.import_label_var.get().strip().lower()

        if not src_path or not os.path.exists(src_path):
            messagebox.showwarning("File Missing", "Please select a valid video file.")
            return

        if not label:
            messagebox.showwarning("Label Required", "Please enter a gesture label name.")
            return

        dest_dir = os.path.join(VIDEO_DIR, label)
        os.makedirs(dest_dir, exist_ok=True)

        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.path.basename(src_path)}"
        dest_path = os.path.join(dest_dir, filename)

        shutil.copyfile(src_path, dest_path)

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO video (path, label, duration) VALUES (?, ?, ?)", (dest_path, label, 3.0))
        conn.commit()
        conn.close()

        self.lbl_import_msg.config(text=f"Successfully imported video '{filename}' into label dataset '{label}'!")
        messagebox.showinfo("Import Complete", f"Imported '{filename}' successfully!")
        self.set_status(f"Imported '{label}' video file.")
        self.refresh_gallery()

    # ==========================================
    # TAB 4: DATASET VIDEO GALLERY
    # ==========================================
    def build_gallery_tab(self):
        container = tk.Frame(self.tab_gallery, bg=self.panel_bg, bd=1, relief="solid")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # Toolbar
        toolbar = tk.Frame(container, bg="#f8fafc", bd=1, relief="solid", padx=12, pady=8)
        toolbar.pack(fill="x", side="top")

        btn_refresh = tk.Button(toolbar, text="🔄 Refresh Gallery", command=self.refresh_gallery, font=('Segoe UI', 9, 'bold'), bg="#e2e8f0", padx=10, pady=3)
        btn_refresh.pack(side="left", padx=(0, 10))

        btn_play = tk.Button(toolbar, text="▶ Play Video", command=self.play_selected_video, font=('Segoe UI', 9, 'bold'), bg="#3b82f6", fg="#ffffff", padx=10, pady=3, bd=0)
        btn_play.pack(side="left", padx=5)

        btn_delete = tk.Button(toolbar, text="🗑️ Delete Selected", command=self.delete_selected_video, font=('Segoe UI', 9, 'bold'), bg="#ef4444", fg="#ffffff", padx=10, pady=3, bd=0)
        btn_delete.pack(side="left", padx=5)

        # Table View (Treeview)
        columns = ("id", "label", "filename", "path", "created_at")
        self.tree = ttk.Treeview(container, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("id", text="ID")
        self.tree.heading("label", text="Gesture Label")
        self.tree.heading("filename", text="Filename")
        self.tree.heading("path", text="Full Storage Path")
        self.tree.heading("created_at", text="Recorded Date")

        self.tree.column("id", width=60, anchor="center")
        self.tree.column("label", width=140, anchor="center")
        self.tree.column("filename", width=220, anchor="w")
        self.tree.column("path", width=380, anchor="w")
        self.tree.column("created_at", width=180, anchor="center")

        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y", pady=10)

        self.refresh_gallery()

    def refresh_gallery(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id, label, path, created_at FROM video ORDER BY id DESC")
        rows = c.fetchall()
        conn.close()

        for r in rows:
            vid_id, label, path, created_at = r
            filename = os.path.basename(path)
            self.tree.insert("", "end", values=(vid_id, label.upper(), filename, path, created_at))

    def play_selected_video(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Selection Required", "Please select a video from the gallery list to play.")
            return

        item = self.tree.item(selected[0])
        path = item['values'][3]

        if not os.path.exists(path):
            messagebox.showerror("File Error", f"Video file not found at path:\n{path}")
            return

        # Open video playback window
        play_win = tk.Toplevel(self.root)
        play_win.title(f"Video Playback - {item['values'][1]}")
        play_win.geometry("660x520")

        canvas = tk.Canvas(play_win, bg="#000000")
        canvas.pack(fill="both", expand=True)

        def play_loop():
            cap = cv2.VideoCapture(path)
            while cap.isOpened() and play_win.winfo_exists():
                ret, frame = cap.read()
                if not ret:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue

                # Process MediaPipe overlay on played video
                landmarks, hands_results, pose_results = self.extract_landmarks_from_frame(frame)
                frame_annotated = self.draw_landmarks(frame.copy(), hands_results, pose_results)

                cv2_img = cv2.cvtColor(frame_annotated, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(cv2_img)
                img = img.resize((640, 480), Image.Resampling.LANCZOS)
                img_tk = ImageTk.PhotoImage(image=img)

                if play_win.winfo_exists():
                    canvas.image_tk = img_tk
                    canvas.create_image(10, 10, image=img_tk, anchor="nw")

                time.sleep(0.04)

            cap.release()

        threading.Thread(target=play_loop, daemon=True).start()

    def delete_selected_video(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Selection Required", "Please select a video from the gallery list to delete.")
            return

        item = self.tree.item(selected[0])
        vid_id = item['values'][0]
        path = item['values'][3]

        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete video ID #{vid_id}?"):
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("DELETE FROM video WHERE id = ?", (vid_id,))
            conn.commit()
            conn.close()

            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass

            self.refresh_gallery()
            messagebox.showinfo("Deleted", "Video deleted successfully.")

    def on_close(self):
        self.is_running = False
        self.is_recording = False
        if self.cap:
            self.cap.release()
        if self.rec_cap:
            self.rec_cap.release()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = SignLanguageDesktopApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
