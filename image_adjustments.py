# image_adjustments.py

import cv2
import numpy as np


class ImageAdjustments:
    def __init__(self):
        self.brightness = 0
        self.contrast = 0
        self.saturation = 0
        self.hue = 0
        self.sharpness = 0
        self.gamma = 1.0

    def reset(self):
        """Resets all adjustments to their default values."""
        self.__init__()

    def adjust_brightness(self, image):
        """Applies the brightness adjustment."""
        if self.brightness != 0:
            if self.brightness > 0:
                shadow = self.brightness
                highlight = 255
            else:
                shadow = 0
                highlight = 255 + self.brightness
            alpha_b = (highlight - shadow) / 255
            gamma_b = shadow
            return cv2.addWeighted(image, alpha_b, image, 0, gamma_b)
        return image

    def adjust_contrast(self, image):
        """Applies the contrast adjustment."""
        if self.contrast != 0:
            f = 131 * (self.contrast + 127) / (127 * (131 - self.contrast))
            alpha_c = f
            gamma_c = 127 * (1 - f)
            return cv2.addWeighted(image, alpha_c, image, 0, gamma_c)
        return image

    def adjust_saturation(self, image):
        """Applies the saturation adjustment."""
        if self.saturation != 0:
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            h, s, v = cv2.split(hsv)
            s = s.astype(np.float32)
            s = s * (self.saturation / 100 + 1)
            s = np.clip(s, 0, 255).astype(np.uint8)
            hsv = cv2.merge([h, s, v])
            return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        return image

    def adjust_hue(self, image):
        """Applies the hue adjustment."""
        if self.hue != 0:
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            h, s, v = cv2.split(hsv)
            h = h.astype(np.float32)
            h = (h + self.hue) % 180
            h = np.clip(h, 0, 180).astype(np.uint8)
            hsv = cv2.merge([h, s, v])
            return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        return image

    def adjust_sharpness(self, image):
        """Applies the sharpness adjustment."""
        if self.sharpness != 0:
            kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
            sharpened = cv2.filter2D(image, -1, kernel)
            return cv2.addWeighted(image, 1 - self.sharpness, sharpened, self.sharpness, 0)
        return image

    def adjust_gamma(self, image):
        """Applies gamma correction."""
        if self.gamma != 1.0:
            inv_gamma = 1.0 / self.gamma
            table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
            return cv2.LUT(image, table)
        return image

    def apply(self, image):
        """Applies all adjustments sequentially."""
        result = image.copy()
        result = self.adjust_brightness(result)
        result = self.adjust_contrast(result)
        result = self.adjust_saturation(result)
        result = self.adjust_hue(result)
        result = self.adjust_sharpness(result)
        result = self.adjust_gamma(result)
        return result

    def update_brightness(self, value):
        """Updates the brightness value."""
        self.brightness = max(-255, min(255, value))

    def update_contrast(self, value):
        """Updates the contrast value."""
        self.contrast = max(-127, min(127, value))

    def update_saturation(self, value):
        """Updates the saturation value."""
        self.saturation = max(-100, min(100, value))

    def update_hue(self, value):
        """Updates the hue value."""
        self.hue = max(-180, min(180, value))

    def update_sharpness(self, value):
        """Updates the sharpness value."""
        self.sharpness = max(0, min(1, value / 100.0)) # Divide by 100 as slider range is 0-100

    def update_gamma(self, value):
        """Updates the gamma value."""
        self.gamma = max(0.1, min(10, value / 100.0)) # Divide by 100 as slider range is 1-200 (representing 0.01-2.00)
