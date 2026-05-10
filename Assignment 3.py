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