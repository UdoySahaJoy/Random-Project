import tkinter as tk
from tkinter import filedialog, messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk
import random
from abc import ABC, abstractmethod

class Alteration(ABC):
    @abstractmethod
    def apply(self, img, x, y, w, h):
        pass

class ColorShiftAlteration(Alteration):
    def apply(self, img, x, y, w, h):
        roi = img[y:y+h, x:x+w]
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        h_channel, s, v = cv2.split(hsv)
        shift = random.randint(20, 60)
        h_channel = np.mod(h_channel.astype(np.int16) + shift, 180).astype(np.uint8)
        shifted_hsv = cv2.merge((h_channel, s, v))
        img[y:y+h, x:x+w] = cv2.cvtColor(shifted_hsv, cv2.COLOR_HSV2BGR)

class BlurAlteration(Alteration):
    def apply(self, img, x, y, w, h):
        roi = img[y:y+h, x:x+w]
        img[y:y+h, x:x+w] = cv2.GaussianBlur(roi, (15, 15), 0)

class BrightnessAlteration(Alteration):
    def apply(self, img, x, y, w, h):
        roi = img[y:y+h, x:x+w]
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        h_channel, s, v = cv2.split(hsv)
        # Randomly increase or decrease brightness by a subtle amount
        shift = random.choice([-40, 40])
        v = np.clip(v.astype(np.int16) + shift, 0, 255).astype(np.uint8)
        shifted_hsv = cv2.merge((h_channel, s, v))
        img[y:y+h, x:x+w] = cv2.cvtColor(shifted_hsv, cv2.COLOR_HSV2BGR)


class ImageManager:
    def __init__(self):
        self._original_image = None
        self._modified_image = None
        self._differences = []
        self.alterations = [ColorShiftAlteration(), BlurAlteration(), BrightnessAlteration()]

    def load_image(self, filepath):
        img = cv2.imread(filepath)
        if img is None:
            return False
        
        max_dim = 500
        h, w = img.shape[:2]
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            img = cv2.resize(img, (int(w * scale), int(h * scale)))

        self._original_image = img
        self._modified_image = img.copy()
        self._generate_differences()
        return True

    def _generate_differences(self):
        self._differences = []
        img_h, img_w = self._modified_image.shape[:2]
        
        diff_size_min = 30
        diff_size_max = 80
        
        attempts = 0
        while len(self._differences) < 5 and attempts < 1000:
            attempts += 1
            dw = random.randint(diff_size_min, diff_size_max)
            dh = random.randint(diff_size_min, diff_size_max)
            
            x = random.randint(0, img_w - dw)
            y = random.randint(0, img_h - dh)
            
            overlap = False
            for diff in self._differences:
                rx, ry, rw, rh = diff['rect']
                if not (x + dw < rx or x > rx + rw or y + dh < ry or y > ry + rh):
                    overlap = True
                    break
            
            if not overlap:
                self._differences.append({'rect': (x, y, dw, dh), 'found': False})
                alt = random.choice(self.alterations)
                alt.apply(self._modified_image, x, y, dw, dh)

    def get_images_for_display(self):
        orig_disp = self._original_image.copy()
        mod_disp = self._modified_image.copy()
        
        for diff in self._differences:
            if diff['found']:
                x, y, w, h = diff['rect']
                center = (x + w//2, y + h//2)
                radius = max(w, h) // 2 + 5
                cv2.circle(orig_disp, center, radius, (0, 0, 255), 2)
                cv2.circle(mod_disp, center, radius, (0, 0, 255), 2)

        return self._cv2_to_photoimage(orig_disp), self._cv2_to_photoimage(mod_disp)

    def get_revealed_images(self):
        orig_disp = self._original_image.copy()
        mod_disp = self._modified_image.copy()
        
        for diff in self._differences:
            x, y, w, h = diff['rect']
            center = (x + w//2, y + h//2)
            radius = max(w, h) // 2 + 5
            color = (0, 0, 255) if diff['found'] else (255, 0, 0)
            cv2.circle(orig_disp, center, radius, color, 2)
            cv2.circle(mod_disp, center, radius, color, 2)

        return self._cv2_to_photoimage(orig_disp), self._cv2_to_photoimage(mod_disp)

    def _cv2_to_photoimage(self, img):
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)
        return ImageTk.PhotoImage(image=pil_img)

    def check_click(self, cx, cy):
        for diff in self._differences:
            if not diff['found']:
                x, y, w, h = diff['rect']
                margin = 10
                if (x - margin <= cx <= x + w + margin) and (y - margin <= cy <= y + h + margin):
                    diff['found'] = True
                    return True
        return False

    def get_unfound_count(self):
        return sum(1 for d in self._differences if not d['found'])
