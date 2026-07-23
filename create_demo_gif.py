import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

def create_demo_gif():
    output_gif_path = os.path.join("app", "static", "img", "test.gif")
    os.makedirs(os.path.dirname(output_gif_path), exist_ok=True)

    w, h = 800, 520
    frames = []

    # Try loading Segoe UI or Arial fonts
    try:
        font_title = ImageFont.truetype("segoeui.ttf", 22)
        font_sub = ImageFont.truetype("segoeui.ttf", 14)
        font_hero = ImageFont.truetype("segoeui.ttf", 28)
        font_bold = ImageFont.truetype("segoeuib.ttf", 16)
        font_normal = ImageFont.truetype("segoeui.ttf", 14)
        font_small = ImageFont.truetype("segoeui.ttf", 12)
    except Exception:
        font_title = font_sub = font_hero = font_bold = font_normal = font_small = ImageFont.load_default()

    # Color Palette
    BG_DARK = (15, 23, 42)
    PANEL_BG = (255, 255, 255)
    PANEL_BORDER = (226, 232, 240)
    HEADER_BG = (248, 250, 252)
    PRIMARY_BLUE = (2, 132, 199)
    LIGHT_BLUE_BG = (224, 242, 254)
    TEXT_DARK = (30, 41, 59)
    TEXT_MUTED = (100, 116, 139)
    GREEN = (16, 185, 129)
    GRAY_BAR = (226, 232, 240)

    # Scenarios to simulate in the GIF
    scenarios = [
        {"label": "AFTERNOON", "conf": 99.4, "top3": [("afternoon", 99.4), ("day", 0.6), ("time", 0.0)], "hand": True},
        {"label": "MONDAY", "conf": 100.0, "top3": [("monday", 100.0), ("day", 0.0), ("name", 0.0)], "hand": True},
        {"label": "NIGHT", "conf": 98.8, "top3": [("night", 98.8), ("day", 1.2), ("people", 0.0)], "hand": True},
        {"label": "TIME", "conf": 96.5, "top3": [("time", 96.5), ("country", 3.2), ("age", 0.3)], "hand": True},
        {"label": "NO HAND DETECTED", "conf": 0.0, "top3": [], "hand": False},
        {"label": "BOY", "conf": 100.0, "top3": [("boy", 100.0), ("person", 0.0), ("name", 0.0)], "hand": True},
    ]

    for sc in scenarios:
        for step in range(12): # 12 frames per scenario (~1.2 sec per gesture)
            img = Image.new("RGB", (w, h), (244, 246, 249))
            draw = ImageDraw.Draw(img)

            # Top Header Bar
            draw.rectangle([15, 12, w - 15, 60], fill=PANEL_BG, outline=PANEL_BORDER)
            draw.text((30, 20), "Real-Time Sign Language Recognition & Translation System", fill=TEXT_DARK, font=font_title)
            draw.text((30, 44), "Pose Keypoint Extraction + LSTM Model (Evaluated Test Accuracy: 98.67%)", fill=TEXT_MUTED, font=font_small)

            # Camera Active indicator
            draw.ellipse([w - 140, 30, w - 130, 40], fill=GREEN)
            draw.text((w - 124, 26), "Camera Active", fill=GREEN, font=font_bold)

            # Left Viewport Panel (Webcam + MediaPipe)
            draw.rectangle([15, 72, 510, h - 35], fill=BG_DARK, outline=PANEL_BORDER)
            draw.rectangle([15, 72, 510, 102], fill=HEADER_BG, outline=PANEL_BORDER)
            draw.text((30, 78), "Live Camera & MediaPipe Keypoint Overlay", fill=TEXT_DARK, font=font_bold)

            # Draw Simulated User Person & Skeleton
            center_x, center_y = 260, 270

            # Head
            draw.ellipse([center_x - 45, center_y - 100, center_x + 45, center_y - 10], outline=(200, 200, 200), width=2)
            # Shoulders
            draw.line([(center_x - 110, center_y + 60), (center_x + 110, center_y + 60)], fill=(200, 200, 200), width=3)
            # Torso
            draw.line([(center_x - 110, center_y + 60), (center_x - 80, center_y + 180)], fill=(200, 200, 200), width=2)
            draw.line([(center_x + 110, center_y + 60), (center_x + 80, center_y + 180)], fill=(200, 200, 200), width=2)

            # Pose Joint Landmark Points (Blue)
            pose_points = [(center_x - 110, center_y + 60), (center_x + 110, center_y + 60), (center_x - 130, center_y + 120), (center_x + 130, center_y + 120)]
            for px, py in pose_points:
                draw.ellipse([px - 6, py - 6, px + 6, py + 6], fill=(255, 0, 0))

            # Hand Skeleton Landmark Tracking (Green)
            if sc["hand"]:
                # Left Hand Skeleton near shoulder/chest
                hx = center_x - 70 + (step % 4) * 3
                hy = center_y + 10 - (step % 3) * 2

                hand_joints = [
                    (hx, hy), (hx - 15, hy - 25), (hx - 5, hy - 40), (hx + 10, hy - 42), (hx + 22, hy - 35), (hx + 30, hy - 20)
                ]
                # Draw hand connections
                for i in range(len(hand_joints) - 1):
                    draw.line([hand_joints[i], hand_joints[i+1]], fill=(0, 255, 0), width=2)
                for jx, jy in hand_joints:
                    draw.ellipse([jx - 4, jy - 4, jx + 4, jy + 4], fill=(0, 255, 0))

                # Right Hand Skeleton
                hrx = center_x + 60 - (step % 3) * 2
                hry = center_y + 15 - (step % 4) * 3
                r_hand_joints = [
                    (hrx, hry), (hrx - 10, hry - 30), (hrx + 5, hry - 45), (hrx + 20, hry - 40), (hrx + 32, hry - 25)
                ]
                for i in range(len(r_hand_joints) - 1):
                    draw.line([r_hand_joints[i], r_hand_joints[i+1]], fill=(0, 255, 0), width=2)
                for jx, jy in r_hand_joints:
                    draw.ellipse([jx - 4, jy - 4, jx + 4, jy + 4], fill=(0, 255, 0))

                # Status label on canvas
                draw.text((30, h - 65), f"MediaPipe Active • Tracking 21 Hand Landmarks", fill=GREEN, font=font_small)
            else:
                draw.text((30, h - 65), "MediaPipe Active • Hand Resting State", fill=TEXT_MUTED, font=font_small)

            # Right Column: Prediction Metrics Panel
            right_x = 525
            right_w = w - right_x - 15
            draw.rectangle([right_x, 72, right_x + right_w, h - 35], fill=PANEL_BG, outline=PANEL_BORDER)
            draw.rectangle([right_x, 72, right_x + right_w, 102], fill=HEADER_BG, outline=PANEL_BORDER)
            draw.text((right_x + 15, 78), "Recognition Predictions", fill=TEXT_DARK, font=font_bold)

            # Hero Card Display
            draw.text((right_x + 15, 115), "PREDICTED SIGN GESTURE", fill=TEXT_MUTED, font=font_small)
            
            hero_bg = LIGHT_BLUE_BG if sc["hand"] else (241, 245, 249)
            hero_border = PRIMARY_BLUE if sc["hand"] else (203, 213, 225)
            draw.rectangle([right_x + 15, 135, right_x + right_w - 15, 215], fill=hero_bg, outline=hero_border, width=2)

            disp_text = sc["label"] if sc["hand"] else "[ NO HAND DETECTED ]"
            disp_color = PRIMARY_BLUE if sc["hand"] else TEXT_MUTED
            
            bbox = draw.textbbox((0, 0), disp_text, font=font_hero)
            tw = bbox[2] - bbox[1]
            draw.text((right_x + (right_w - tw)//2 - 15, 160), disp_text, fill=disp_color, font=font_hero)

            # Top 3 Progress Meters
            draw.text((right_x + 15, 230), "TOP 3 CONFIDENCE PROBABILITIES", fill=TEXT_MUTED, font=font_small)

            if sc["hand"] and sc["top3"]:
                for i, (name, val) in enumerate(sc["top3"]):
                    box_y = 250 + i * 55
                    draw.rectangle([right_x + 15, box_y, right_x + right_w - 15, box_y + 48], fill=(248, 250, 252), outline=PANEL_BORDER)
                    
                    draw.text((right_x + 25, box_y + 6), f"{i+1}. {name.upper()}", fill=TEXT_DARK, font=font_bold)
                    draw.text((right_x + right_w - 70, box_y + 6), f"{val:.1f}%", fill=PRIMARY_BLUE, font=font_bold)

                    # Progress bar track
                    draw.rectangle([right_x + 25, box_y + 28, right_x + right_w - 25, box_y + 36], fill=GRAY_BAR)
                    bar_w = int((val / 100.0) * (right_w - 50))
                    if bar_w > 0:
                        draw.rectangle([right_x + 25, box_y + 28, right_x + 25 + bar_w, box_y + 36], fill=PRIMARY_BLUE)
            else:
                for i in range(3):
                    box_y = 250 + i * 55
                    draw.rectangle([right_x + 15, box_y, right_x + right_w - 15, box_y + 48], fill=(248, 250, 252), outline=PANEL_BORDER)
                    draw.text((right_x + 25, box_y + 6), f"{i+1}. -", fill=TEXT_MUTED, font=font_bold)
                    draw.text((right_x + right_w - 70, box_y + 6), "0.0%", fill=TEXT_MUTED, font=font_bold)
                    draw.rectangle([right_x + 25, box_y + 28, right_x + right_w - 25, box_y + 36], fill=GRAY_BAR)

            # Footer Metrics Box
            draw.rectangle([right_x + 15, h - 90, right_x + right_w - 15, h - 45], fill=(241, 245, 249), outline=PANEL_BORDER)
            draw.text((right_x + 25, h - 85), "ACCURACY & METRICS", fill=TEXT_MUTED, font=font_small)
            draw.text((right_x + 25, h - 65), "• Test Accuracy: 98.67% | F1: 0.99", fill=GREEN, font=font_bold)

            # Bottom Status Bar
            draw.rectangle([0, h - 26, w, h], fill=(226, 232, 240))
            draw.text((15, h - 20), "Status: Live translation loop active | Audio TTS enabled", fill=TEXT_DARK, font=font_small)

            frames.append(img)

    # Save as animated GIF
    frames[0].save(output_gif_path, save_all=True, append_images=frames[1:], duration=120, loop=0)
    print(f"Demo GIF created successfully at: {output_gif_path} ({len(frames)} frames)")

if __name__ == "__main__":
    create_demo_gif()
