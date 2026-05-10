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

class GameApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Spot the Difference")
        
        self.image_manager = ImageManager()
        self.cumulative_score = 0
        self.mistakes = 0
        self.max_mistakes = 3
        self.game_over = False

        self._setup_gui()

    def _setup_gui(self):
        self.top_frame = tk.Frame(self.root, padx=10, pady=10)
        self.top_frame.pack(fill=tk.X)

        self.btn_load = tk.Button(self.top_frame, text="Load Image", command=self.load_image)
        self.btn_load.pack(side=tk.LEFT, padx=5)

        self.btn_reveal = tk.Button(self.top_frame, text="Reveal", command=self.reveal, state=tk.DISABLED)
        self.btn_reveal.pack(side=tk.LEFT, padx=5)

        self.lbl_score = tk.Label(self.top_frame, text="Cumulative Score: 0", font=("Arial", 12, "bold"))
        self.lbl_score.pack(side=tk.LEFT, padx=20)

        self.lbl_unfound = tk.Label(self.top_frame, text="Remaining: 0", font=("Arial", 12, "bold"))
        self.lbl_unfound.pack(side=tk.LEFT, padx=20)

        self.lbl_mistakes = tk.Label(self.top_frame, text="Mistakes: 0/3", font=("Arial", 12, "bold"), fg="red")
        self.lbl_mistakes.pack(side=tk.LEFT, padx=20)

        self.main_content = tk.Frame(self.root)
        self.main_content.pack(fill=tk.BOTH, expand=True)

        self.lbl_orig_title = tk.Label(self.main_content, text="Original Image", font=("Arial", 12))
        self.lbl_orig_title.grid(row=0, column=0, pady=5)
        
        self.lbl_mod_title = tk.Label(self.main_content, text="Modified Image (Click Here)", font=("Arial", 12))
        self.lbl_mod_title.grid(row=0, column=1, pady=5)

        self.canvas_orig = tk.Canvas(self.main_content, bg="gray", width=500, height=500)
        self.canvas_orig.grid(row=1, column=0, padx=10, pady=10)

        self.canvas_mod = tk.Canvas(self.main_content, bg="gray", width=500, height=500)
        self.canvas_mod.grid(row=1, column=1, padx=10, pady=10)

        self.canvas_mod.bind("<Button-1>", self.on_image_click)

        self.photo_orig = None
        self.photo_mod = None

    def load_image(self):
        filepath = filedialog.askopenfilename(filetypes=[("Image Files", "*.jpg *.png *.bmp *.jpeg")])
        if filepath:
            if self.image_manager.load_image(filepath):
                self.mistakes = 0
                self.game_over = False
                self.btn_reveal.config(state=tk.NORMAL)
                self.update_display()
            else:
                messagebox.showerror("Error", "Failed to load image.")

    def update_display(self):
        self.photo_orig, self.photo_mod = self.image_manager.get_images_for_display()
        
        self.canvas_orig.config(width=self.photo_orig.width(), height=self.photo_orig.height())
        self.canvas_orig.create_image(0, 0, anchor=tk.NW, image=self.photo_orig)

        self.canvas_mod.config(width=self.photo_mod.width(), height=self.photo_mod.height())
        self.canvas_mod.create_image(0, 0, anchor=tk.NW, image=self.photo_mod)

        unfound = self.image_manager.get_unfound_count()
        self.lbl_unfound.config(text=f"Remaining: {unfound}")
        self.lbl_score.config(text=f"Cumulative Score: {self.cumulative_score}")
        self.lbl_mistakes.config(text=f"Mistakes: {self.mistakes}/{self.max_mistakes}")

    def on_image_click(self, event):
        if self.game_over or self.image_manager._modified_image is None:
            return

        cx, cy = event.x, event.y
        hit = self.image_manager.check_click(cx, cy)
        
        if hit:
            self.cumulative_score += 1
            unfound = self.image_manager.get_unfound_count()
            self.update_display()
            if unfound == 0:
                self.game_over = True
                messagebox.showinfo("Success", "You found all differences! Load a new image to continue.")
        else:
            self.mistakes += 1
            self.update_display()
            if self.mistakes >= self.max_mistakes:
                self.game_over = True
                found_current = 5 - self.image_manager.get_unfound_count()
                messagebox.showwarning("Game Over", f"Too many mistakes! You found {found_current} differences.\nLoad a new image to restart.")

    def reveal(self):
        if self.image_manager._modified_image is None:
            return

        self.game_over = True
        self.photo_orig, self.photo_mod = self.image_manager.get_revealed_images()
        
        self.canvas_orig.create_image(0, 0, anchor=tk.NW, image=self.photo_orig)
        self.canvas_mod.create_image(0, 0, anchor=tk.NW, image=self.photo_mod)
        messagebox.showinfo("Revealed", "All differences have been revealed. Load a new image to continue.")


if __name__ == "__main__":
    root = tk.Tk()
    app = GameApp(root)
    root.mainloop()
