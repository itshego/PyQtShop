# image_operations.py

import cv2
import numpy as np


class ImageOperations:
    @staticmethod
    def open_image(filename):
        """Opens an image from a file."""
        return cv2.imread(filename)

    @staticmethod
    def save_image(filename, image):
        """Saves the image to a file."""
        cv2.imwrite(filename, image)

    @staticmethod
    def create_new_image(width, height, color=(255, 255, 255)):
        """Creates a new image with the specified dimensions."""
        return np.full((height, width, 3), color, dtype=np.uint8)

    @staticmethod
    def flip(image, axis):
        """Flips the image horizontally or vertically."""
        if axis == "Horizontal":
            return cv2.flip(image, 1)
        elif axis == "Vertical":
            return cv2.flip(image, 0)
        else:
            raise ValueError("Axis must be either 'Horizontal' or 'Vertical'")

    @staticmethod
    def rotate(image, direction):
        """Rotates the image 90 degrees clockwise or counter-clockwise."""
        if direction == "cw":
            return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        elif direction == "ccw":
            return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        else:
            raise ValueError("Direction must be either 'cw' or 'ccw'")

    @staticmethod
    def convert_to_gray(image):
        """Converts the image to grayscale."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    @staticmethod
    def convert_to_rgb(image):
        """Converts the image to RGB color space."""
        return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    @staticmethod
    def convert_to_hsv(image):
        """Converts the image to HSV color space."""
        return cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    @staticmethod
    def convert_to_sepia(image):
        """Applies a sepia effect to the image."""
        kernel = np.array([[0.272, 0.534, 0.131],
                           [0.349, 0.686, 0.168],
                           [0.393, 0.769, 0.189]])
        return cv2.transform(image, kernel)

    @staticmethod
    def crop_image(image, x, y, width, height):
        """Crops the image based on the specified coordinates."""
        return image[y:y+height, x:x+width]

    @staticmethod
    def resize_image(image, width, height):
        """Resizes the image to the specified dimensions."""
        return cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)

    @staticmethod
    def apply_gaussian_blur(image, kernel_size=(5, 5)):
        """Applies Gaussian blur to the image."""
        return cv2.GaussianBlur(image, kernel_size, 0)

    @staticmethod
    def apply_median_blur(image, kernel_size=5):
        """Applies median blur to the image."""
        return cv2.medianBlur(image, kernel_size)

    @staticmethod
    def detect_edges(image, threshold1=100, threshold2=200):
        """Detects edges in the image using the Canny edge detection algorithm."""
        return cv2.Canny(image, threshold1, threshold2)

    @staticmethod
    def equalize_histogram(image):
        """Equalizes the histogram of the image."""
        ycrcb = cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)
        channels = cv2.split(ycrcb)
        cv2.equalizeHist(channels[0], channels[0])
        ycrcb = cv2.merge(channels)
        return cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)
