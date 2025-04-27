# PyQt5 Image Editor

A simple image editor application built with PyQt5 and OpenCV.

## Features

*   Open, save, and create new images (including from clipboard).
*   Basic image viewing with zoom functionality.
*   Drawing tools: Brush, Text, Shapes (Circle, Rectangle, Line).
*   Image adjustments: Brightness, Contrast, Saturation, Hue, Sharpness, Gamma.
*   Image filters: Grayscale, RGB, HSV, Sepia, Gaussian Blur, Median Blur, Histogram Equalization.
*   Image operations: Flip (Horizontal, Vertical), Rotate (CW, CCW), Crop.
*   Color picking (Eyedropper).
*   Undo functionality for drawing and image operations.
*   Draggable shapes and text items.
*   Debug panel for development insights.

## Requirements

*   Python 3.x
*   PyQt5
*   OpenCV-Python (`opencv-python`)
*   NumPy

You can install the required packages using the `requirements.txt` file:

```bash
pip install -r requirements.txt
```

## Usage

Run the main application file:

```bash
python main.py
```

## Development

The application uses `cProfile` for profiling. When the application closes, it saves profiling data to `profile_data.prof`. You can analyze this file using tools like `snakeviz`:

```bash
pip install snakeviz
snakeviz profile_data.prof
```

## License

(Optional: Add license information here, e.g., MIT License) 