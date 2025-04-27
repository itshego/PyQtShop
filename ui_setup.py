from PyQt5.QtWidgets import (QAction, QFileDialog, QLabel, QDockWidget, QVBoxLayout, 
                           QWidget, QSlider, QApplication, QMessageBox, QPushButton, 
                           QFontDialog, QHBoxLayout, QToolButton, QMenu, 
                           QActionGroup, QLineEdit, QComboBox)
from PyQt5.QtGui import QIcon, QPixmap, QColor, QFont
from PyQt5.QtCore import Qt

class UISetup:
    def __init__(self, main_window):
        self.main_window = main_window
        # Initialize UI elements that might be accessed by handlers BEFORE handlers are connected
        self.main_window.tools_toolbar = None 
        self.main_window.shape_button = None
        self.main_window.flip_rotate_button = None
        self.main_window.brush_size_slider = None
        self.main_window.brush_size_input = None
        self.main_window.brush_opacity_slider = None
        self.main_window.brush_opacity_input = None
        self.main_window.penStyleComboBox = None
        self.main_window.penCapComboBox = None
        self.main_window.penJoinComboBox = None
        self.main_window.brushStyleComboBox = None
        self.main_window.color_dock = None

    def init_ui(self):
        mw = self.main_window 
        # Ensure event_handlers exists before connecting signals
        if not hasattr(mw, 'event_handlers') or mw.event_handlers is None:
             # This should not happen if __init__ order is correct
             print("ERROR: Event Handlers not initialized before UI Setup!")
             return 
             
        mw.setWindowTitle("Image Editor")
        mw.setGeometry(100, 100, 800, 600)
        self.create_actions()       # Connects actions to event_handlers
        self.create_menus()         # Adds actions to menus
        self.create_toolbars()      # Connects buttons/menus to event_handlers
        self.create_adjustment_dock() # Connects sliders to event_handlers
        self.create_filters_dock()    # Connects buttons to event_handlers
        self.create_color_panel()     # Connects buttons/labels to event_handlers
        
        mw.statusBar().showMessage('Ready')

    def create_actions(self):
        mw = self.main_window
        eh = mw.event_handlers # Alias for event handlers

        # File Actions - Connect to event handlers
        mw.open_act = QAction(QIcon('icons/open.png'), 'Open', mw)
        mw.open_act.setShortcut('Ctrl+O'); mw.open_act.setStatusTip('Open image')
        mw.open_act.triggered.connect(eh.open_image)

        mw.save_act = QAction(QIcon('icons/save.png'), 'Save', mw)
        mw.save_act.setShortcut('Ctrl+S'); mw.save_act.setStatusTip('Save image')
        mw.save_act.triggered.connect(eh.save_image)

        mw.new_act = QAction(QIcon('icons/new.png'), 'New', mw)
        mw.new_act.setShortcut('Ctrl+N'); mw.new_act.setStatusTip('New image')
        mw.new_act.triggered.connect(eh.new_image)

        mw.exit_act = QAction(QIcon('icons/exit.png'), 'Exit', mw)
        mw.exit_act.setShortcut('Ctrl+Q'); mw.exit_act.setStatusTip('Exit application')
        mw.exit_act.triggered.connect(mw.close) # Close is a QMainWindow method

        # Rotate and Flip Actions - Connect to event handlers
        mw.flip_rotate_group = QActionGroup(mw)
        mw.flip_h_act = QAction(QIcon('icons/flip_h.png'), 'Flip Horizontal', mw)
        mw.flip_h_act.setStatusTip('Flip image horizontally'); mw.flip_h_act.setCheckable(True); mw.flip_h_act.setChecked(True)
        mw.flip_v_act = QAction(QIcon('icons/flip_v.png'), 'Flip Vertical', mw)
        mw.flip_v_act.setStatusTip('Flip image vertically'); mw.flip_v_act.setCheckable(True)
        mw.rotate_cw_act = QAction(QIcon('icons/rotate_cw.png'), 'Rotate CW', mw)
        mw.rotate_cw_act.setStatusTip('Rotate image clockwise'); mw.rotate_cw_act.setCheckable(True)
        mw.rotate_ccw_act = QAction(QIcon('icons/rotate_ccw.png'), 'Rotate CCW', mw)
        mw.rotate_ccw_act.setStatusTip('Rotate image counter-clockwise'); mw.rotate_ccw_act.setCheckable(True)
        mw.flip_rotate_group.addAction(mw.flip_h_act)
        mw.flip_rotate_group.addAction(mw.flip_v_act)
        mw.flip_rotate_group.addAction(mw.rotate_cw_act)
        mw.flip_rotate_group.addAction(mw.rotate_ccw_act)
        # Group trigger connects to icon updater in handlers
        # mw.flip_rotate_group.triggered.connect(eh.update_flip_rotate_button_icon) # Moved connection to toolbar menu

        # Shape Actions - Connect to event handlers
        mw.shape_group = QActionGroup(mw)
        mw.shape_group.setExclusive(True)
        mw.circle_act = QAction(QIcon('icons/circle.png'), 'Circle', mw)
        mw.circle_act.setStatusTip('Draw circle'); mw.circle_act.setCheckable(True); mw.circle_act.setChecked(True)
        mw.rectangle_act = QAction(QIcon('icons/rectangle.png'), 'Rectangle', mw)
        mw.rectangle_act.setStatusTip('Draw rectangle'); mw.rectangle_act.setCheckable(True)
        mw.line_act = QAction(QIcon('icons/line.png'), 'Line', mw)
        mw.line_act.setStatusTip('Draw line'); mw.line_act.setCheckable(True)
        mw.path_act = QAction(QIcon('icons/path.png'), 'Path', mw)
        mw.path_act.setStatusTip('Draw path'); mw.path_act.setCheckable(True)
        mw.polygon_act = QAction(QIcon('icons/polygon.png'), 'Polygon', mw)
        mw.polygon_act.setStatusTip('Draw polygon'); mw.polygon_act.setCheckable(True)
        mw.pixmap_act = QAction(QIcon('icons/pixmap.png'), 'Pixmap', mw)
        mw.pixmap_act.setStatusTip('Insert pixmap'); mw.pixmap_act.setCheckable(True)
        mw.shape_group.addAction(mw.circle_act)
        mw.shape_group.addAction(mw.rectangle_act)
        mw.shape_group.addAction(mw.line_act)
        mw.shape_group.addAction(mw.path_act)
        mw.shape_group.addAction(mw.polygon_act)
        mw.shape_group.addAction(mw.pixmap_act)
        mw.shape_group.triggered.connect(eh.shape_tool_changed)

        # Filter Actions - Connect to event handlers
        mw.gray_act = QAction(QIcon('icons/gray.png'), 'Convert to Grayscale', mw)
        mw.gray_act.setStatusTip('Convert image to grayscale'); mw.gray_act.triggered.connect(eh.convert_to_gray)
        mw.rgb_act = QAction(QIcon('icons/rgb.png'), 'Convert to RGB', mw)
        mw.rgb_act.setStatusTip('Convert image to RGB'); mw.rgb_act.triggered.connect(eh.convert_to_rgb)
        mw.hsv_act = QAction(QIcon('icons/hsv.png'), 'Convert to HSV', mw)
        mw.hsv_act.setStatusTip('Convert image to HSV'); mw.hsv_act.triggered.connect(eh.convert_to_hsv)
        mw.sepia_act = QAction(QIcon('icons/sepia.png'), 'Apply Sepia', mw)
        mw.sepia_act.setStatusTip('Apply sepia filter'); mw.sepia_act.triggered.connect(eh.convert_to_sepia)
        mw.gaussian_blur_act = QAction(QIcon('icons/gaussian.png'), 'Apply Gaussian Blur', mw)
        mw.gaussian_blur_act.setStatusTip('Apply Gaussian blur'); mw.gaussian_blur_act.triggered.connect(eh.apply_gaussian_blur)
        mw.median_blur_act = QAction(QIcon('icons/median.png'), 'Apply Median Blur', mw)
        mw.median_blur_act.setStatusTip('Apply Median blur'); mw.median_blur_act.triggered.connect(eh.apply_median_blur)
        mw.equalize_hist_act = QAction(QIcon('icons/equalize.png'), 'Equalize Histogram', mw)
        mw.equalize_hist_act.setStatusTip('Equalize image histogram'); mw.equalize_hist_act.triggered.connect(eh.equalize_histogram)

        # Edit Actions - Connect to event handlers or view directly
        mw.brush_act = QAction(QIcon('icons/brush.png'), 'Brush', mw)
        mw.brush_act.setShortcut('B'); mw.brush_act.setStatusTip('Use brush tool')
        mw.brush_act.triggered.connect(eh.select_brush_tool)

        mw.text_act = QAction(QIcon('icons/font.png'), 'Text', mw)
        mw.text_act.setShortcut('T'); mw.text_act.setStatusTip('Add text to image')
        mw.text_act.triggered.connect(lambda: mw.view.set_tool('text')) # Directly sets view tool

        mw.crop_act = QAction(QIcon('icons/crop.png'), 'Crop', mw)
        mw.crop_act.setShortcut('C'); mw.crop_act.setStatusTip('Crop image')
        mw.crop_act.triggered.connect(lambda: mw.view.set_tool('crop')) # Directly sets view tool

        mw.eyedropper_act = QAction(QIcon('icons/eyedropper.png'), 'Eyedropper', mw)
        mw.eyedropper_act.setShortcut('E'); mw.eyedropper_act.setStatusTip('Pick color from image')
        mw.eyedropper_act.triggered.connect(lambda: mw.view.set_tool('eyedropper')) # Directly sets view tool

        mw.zoom_act = QAction(QIcon('icons/zoom.png'), 'Zoom', mw)
        mw.zoom_act.setShortcut('Z'); mw.zoom_act.setStatusTip('Zoom in/out')
        mw.zoom_act.triggered.connect(lambda: mw.view.set_tool('zoom')) # Directly sets view tool

        mw.undo_act = QAction(QIcon('icons/undo.png'), 'Undo', mw)
        mw.undo_act.setShortcut('Ctrl+Z'); mw.undo_act.setStatusTip('Undo last action')
        mw.undo_act.triggered.connect(eh.undo) # Connect to handler

        mw.font_act = QAction(QIcon('icons/text.png'), 'Change Font', mw)
        mw.font_act.setShortcut('Ctrl+F'); mw.font_act.setStatusTip('Change text font')
        mw.font_act.triggered.connect(eh.change_font) # Connect to handler

        mw.move_act = QAction(QIcon('icons/move.png'), 'Move', mw)
        mw.move_act.setShortcut('V'); mw.move_act.setStatusTip('Move tool')
        mw.move_act.triggered.connect(lambda: mw.view.set_tool('move')) # Directly sets view tool

        mw.swap_colors_act = QAction('SwapColors', mw)
        mw.swap_colors_act.setShortcut('X')
        mw.swap_colors_act.triggered.connect(eh.swap_colors) # Connect to handler

        mw.rotate_or_flip_act = QAction('RotateOrFlip', mw)
        mw.rotate_or_flip_act.setShortcut('R')
        mw.rotate_or_flip_act.triggered.connect(eh.perform_flip_rotate) # Connect to handler

    def create_menus(self):
        mw = self.main_window
        menubar = mw.menuBar()
        menubar.setNativeMenuBar(False)
        menubar.setFocusPolicy(Qt.NoFocus)

        file_menu = menubar.addMenu('File')
        file_menu.addAction(mw.new_act)
        file_menu.addAction(mw.open_act)
        file_menu.addAction(mw.save_act)
        file_menu.addSeparator()
        file_menu.addAction(mw.exit_act)

        flip_rotate_menu = menubar.addMenu('Rotate and Flip') # Changed menu name for clarity
        flip_rotate_menu.addAction(mw.flip_h_act)
        flip_rotate_menu.addAction(mw.flip_v_act)
        flip_rotate_menu.addAction(mw.rotate_cw_act)
        flip_rotate_menu.addAction(mw.rotate_ccw_act)

        edit_menu = menubar.addMenu('Edit')
        edit_menu.addAction(mw.undo_act) # Undo action
        edit_menu.addSeparator()
        edit_menu.addAction(mw.brush_act)
        edit_menu.addAction(mw.text_act)
        edit_menu.addAction(mw.font_act) # Font action
        edit_menu.addSeparator()
        edit_menu.addAction(mw.crop_act)
        edit_menu.addAction(mw.move_act)
        edit_menu.addAction(mw.eyedropper_act)
        edit_menu.addAction(mw.zoom_act)
        edit_menu.addSeparator()
        edit_menu.addAction(mw.swap_colors_act)
        edit_menu.addAction(mw.rotate_or_flip_act)

        filter_menu = menubar.addMenu('Filters')
        filter_menu.addAction(mw.gray_act)
        filter_menu.addAction(mw.rgb_act)
        filter_menu.addAction(mw.hsv_act)
        filter_menu.addAction(mw.sepia_act)
        filter_menu.addSeparator()
        filter_menu.addAction(mw.gaussian_blur_act)
        filter_menu.addAction(mw.median_blur_act)
        filter_menu.addSeparator()
        filter_menu.addAction(mw.equalize_hist_act)
        
    def create_toolbars(self):
        mw = self.main_window
        eh = mw.event_handlers

        # Edit Toolbar
        edit_toolbar = mw.addToolBar('Edit')
        edit_toolbar.addAction(mw.move_act)
        edit_toolbar.addAction(mw.crop_act)
        edit_toolbar.addAction(mw.eyedropper_act)
        edit_toolbar.addAction(mw.brush_act)
        edit_toolbar.addAction(mw.text_act)
        edit_toolbar.addAction(mw.font_act)

        # Shapes Button - Connect to handlers
        mw.shape_button = QToolButton(mw)
        mw.shape_button.setIcon(QIcon('icons/circle.png'))
        mw.shape_button.setPopupMode(QToolButton.MenuButtonPopup)
        mw.shape_button.setToolButtonStyle(Qt.ToolButtonIconOnly)
        mw.shape_button.setToolTip("Shape Tools (U)")
        mw.shape_button.clicked.connect(eh.shape_button_clicked)
        shape_menu = QMenu(mw.shape_button)
        shape_menu.addAction(mw.circle_act)
        shape_menu.addAction(mw.rectangle_act)
        shape_menu.addAction(mw.line_act)
        shape_menu.addAction(mw.path_act)
        shape_menu.addAction(mw.polygon_act)
        shape_menu.addAction(mw.pixmap_act)
        mw.shape_button.setMenu(shape_menu)
        shape_menu.triggered.connect(eh.update_shape_button_icon) # Connects menu trigger
        edit_toolbar.addWidget(mw.shape_button)

        edit_toolbar.addAction(mw.zoom_act)
        edit_toolbar.addAction(mw.undo_act)

        # Flip and Rotate Button - Connect to handlers
        mw.flip_rotate_button = QToolButton(mw)
        mw.flip_rotate_button.setIcon(QIcon('icons/flip_h.png'))
        mw.flip_rotate_button.setPopupMode(QToolButton.MenuButtonPopup)
        mw.flip_rotate_button.setToolButtonStyle(Qt.ToolButtonIconOnly)
        mw.flip_rotate_button.setToolTip("Rotate/Flip Tools (R)")
        mw.flip_rotate_button.clicked.connect(eh.perform_flip_rotate)
        flip_rotate_menu = QMenu(mw.flip_rotate_button)
        flip_rotate_menu.addAction(mw.flip_h_act)
        flip_rotate_menu.addAction(mw.flip_v_act)
        flip_rotate_menu.addAction(mw.rotate_cw_act)
        flip_rotate_menu.addAction(mw.rotate_ccw_act)
        mw.flip_rotate_button.setMenu(flip_rotate_menu)
        flip_rotate_menu.triggered.connect(eh.update_flip_rotate_button_icon) # Connects menu trigger
        edit_toolbar.addWidget(mw.flip_rotate_button)
        
        mw.addToolBar(Qt.LeftToolBarArea, edit_toolbar)

    def create_adjustment_dock(self):
        mw = self.main_window
        eh = mw.event_handlers
        dock = QDockWidget("Adjustments", mw)
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Connect sliders to handler
        self.create_slider(layout, "Brightness", -255, 255, mw.adjustments.update_brightness, eh.apply_adjustments)
        self.create_slider(layout, "Contrast", -127, 127, mw.adjustments.update_contrast, eh.apply_adjustments)
        self.create_slider(layout, "Saturation", -100, 100, mw.adjustments.update_saturation, eh.apply_adjustments)
        self.create_slider(layout, "Hue", -180, 180, mw.adjustments.update_hue, eh.apply_adjustments)
        # Sharpness and Gamma lambda slots call adjustment methods directly, apply_adjustments handles the view update
        self.create_slider(layout, "Sharpness", 0, 100, lambda x: mw.adjustments.update_sharpness(x / 100), eh.apply_adjustments)
        self.create_slider(layout, "Gamma", 1, 200, lambda x: mw.adjustments.update_gamma(x / 100), eh.apply_adjustments)

        dock.setWidget(widget)
        mw.addDockWidget(Qt.RightDockWidgetArea, dock)

    def create_slider(self, layout, label, min_val, max_val, adjustment_slot, apply_slot):
        mw = self.main_window
        layout.addWidget(QLabel(label))
        slider = QSlider(Qt.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(0)
        if label == "Gamma": slider.setValue(100)
        slider.setTickPosition(QSlider.TicksBelow)
        slider.setTickInterval(int((max_val - min_val) / 10))
        slider.valueChanged.connect(adjustment_slot) # Connect to ImageAdjustments update method
        slider.valueChanged.connect(apply_slot)      # Connect to EventHandlers apply_adjustments method
        layout.addWidget(slider)
        mw.adjustment_sliders[label] = slider 

    def create_filters_dock(self):
        mw = self.main_window
        eh = mw.event_handlers
        dock = QDockWidget("Filters", mw)
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        widget = QWidget()
        layout = QVBoxLayout(widget)

        buttons = [
            ('Grayscale', eh.convert_to_gray),
            ('RGB', eh.convert_to_rgb),
            ('HSV', eh.convert_to_hsv),
            ('Sepia', eh.convert_to_sepia),
            ('Gaussian Blur', eh.apply_gaussian_blur),
            ('Median Blur', eh.apply_median_blur),
            ('Equalize Histogram', eh.equalize_histogram)
        ]

        for text, slot in buttons:
            button = QPushButton(text)
            button.clicked.connect(slot) 
            layout.addWidget(button)

        separator = QWidget(); separator.setFixedHeight(2); separator.setStyleSheet("background-color: #c0c0c0;")
        layout.addWidget(separator)

        reset_button = QPushButton("Reset Image")
        reset_button.clicked.connect(mw.event_handlers.reset_image) # Connect to event handler's reset method
        layout.addWidget(reset_button)

        dock.setWidget(widget)
        mw.addDockWidget(Qt.RightDockWidgetArea, dock)
        
    def create_color_panel(self):
        mw = self.main_window
        eh = mw.event_handlers
        mw.color_dock = QDockWidget("Color Panel", mw)
        mw.color_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        mw.color_dock.setFeatures(QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetMovable)

        color_widget = QWidget()
        color_layout = QVBoxLayout(color_widget); color_layout.setAlignment(Qt.AlignCenter)

        preview_layout = QHBoxLayout(); preview_size = 60

        mw.color_preview = QLabel(); mw.color_preview.setFixedSize(preview_size, preview_size)
        mw.update_color_preview() 
        preview_layout.addWidget(mw.color_preview)

        mw.color_preview_2 = QLabel(); mw.color_preview_2.setFixedSize(preview_size, preview_size)
        mw.update_color_preview_2() 
        preview_layout.addWidget(mw.color_preview_2)
        color_layout.addLayout(preview_layout)

        # Connect mouse events to handler methods
        mw.color_preview.mousePressEvent = lambda event, handler=eh: handler.choose_color(1) 
        mw.color_preview_2.mousePressEvent = lambda event, handler=eh: handler.choose_color(2)

        rgb_widget = QWidget(); rgb_layout = QHBoxLayout(rgb_widget); rgb_layout.setContentsMargins(0, 5, 0, 0)
        for label in (mw.r_label, mw.g_label, mw.b_label):
            label.setAlignment(Qt.AlignCenter); rgb_layout.addWidget(label)
        color_layout.addWidget(rgb_widget)

        color_layout.addSpacing(7)
        swap_button = QPushButton("Swap Colors (x)")
        swap_button.clicked.connect(eh.swap_colors) # Connect to handler
        color_layout.addWidget(swap_button)

        mw.color_dock.setWidget(color_widget)
        mw.addDockWidget(Qt.RightDockWidgetArea, mw.color_dock)
        mw.color_dock.setFixedWidth(preview_size * 2 + 20)

    def create_tools_toolbar(self):
        mw = self.main_window
        if mw.tools_toolbar is None:
            mw.tools_toolbar = mw.addToolBar('Tools')
            self.add_brush_size_controls()
            self.add_brush_opacity_controls()
            self.add_pen_style_controls()
            self.add_pen_cap_controls()
            self.add_pen_join_controls()
            self.add_brush_style_controls()
        else:
            # Make sure controls are visible
            for w in [mw.brush_size_slider, mw.brush_size_input, mw.brush_opacity_slider,
                      mw.brush_opacity_input, mw.penStyleComboBox, mw.penCapComboBox,
                      mw.penJoinComboBox, mw.brushStyleComboBox]:
                if w: w.setVisible(True)
            mw.tools_toolbar.setVisible(True)

    # --- Toolbar Control Creation (Connect signals to handlers) --- 
    def add_brush_size_controls(self):
        mw = self.main_window; eh = mw.event_handlers; toolbar = mw.tools_toolbar
        spacer = QWidget(); spacer.setFixedWidth(40); toolbar.addWidget(spacer)
        toolbar.addWidget(QLabel("Brush Size:"))
        mw.brush_size_slider = QSlider(Qt.Horizontal); mw.brush_size_slider.setRange(1, 300)
        mw.brush_size_slider.setValue(20); mw.brush_size_slider.setFixedWidth(100)
        mw.brush_size_slider.valueChanged.connect(eh.change_brush_size) # Connect to handler
        toolbar.addWidget(mw.brush_size_slider)
        spacer = QWidget(); spacer.setFixedWidth(10); toolbar.addWidget(spacer)
        mw.brush_size_input = QLineEdit(f"{mw.brush_size_slider.value()}"); mw.brush_size_input.setFixedWidth(30)
        mw.brush_size_slider.valueChanged.connect(lambda value, inp=mw.brush_size_input: inp.setText(str(value)))
        mw.brush_size_input.editingFinished.connect(eh.update_brush_size_from_input) # Connect to handler
        toolbar.addWidget(mw.brush_size_input)

    def add_brush_opacity_controls(self):
        mw = self.main_window; eh = mw.event_handlers; toolbar = mw.tools_toolbar
        spacer = QWidget(); spacer.setFixedWidth(40); toolbar.addWidget(spacer)
        toolbar.addWidget(QLabel("Opacity:"))
        mw.brush_opacity_slider = QSlider(Qt.Horizontal); mw.brush_opacity_slider.setRange(0, 100)
        mw.brush_opacity_slider.setValue(100); mw.brush_opacity_slider.setFixedWidth(100)
        mw.brush_opacity_slider.valueChanged.connect(mw.view.set_brush_opacity) # Connect directly to view
        toolbar.addWidget(mw.brush_opacity_slider)
        spacer = QWidget(); spacer.setFixedWidth(10); toolbar.addWidget(spacer)
        mw.brush_opacity_input = QLineEdit(f"{mw.brush_opacity_slider.value()}"); mw.brush_opacity_input.setFixedWidth(30)
        mw.brush_opacity_slider.valueChanged.connect(lambda value, inp=mw.brush_opacity_input: inp.setText(str(value)))
        mw.brush_opacity_input.editingFinished.connect(eh.update_brush_opacity_from_input) # Connect to handler
        toolbar.addWidget(mw.brush_opacity_input)

    def add_pen_style_controls(self):
        mw = self.main_window; eh = mw.event_handlers; toolbar = mw.tools_toolbar
        spacer = QWidget(); spacer.setFixedWidth(10); toolbar.addWidget(spacer)
        toolbar.addWidget(QLabel("Pen Style:"))
        mw.penStyleComboBox = QComboBox()
        items = [("Solid", Qt.SolidLine), ("Dash", Qt.DashLine), ("Dot", Qt.DotLine),
                 ("Dash Dot", Qt.DashDotLine), ("Dash Dot Dot", Qt.DashDotDotLine), ("None", Qt.NoPen)]
        for text, data in items: mw.penStyleComboBox.addItem(text, data)
        mw.penStyleComboBox.currentIndexChanged.connect(eh.update_pen_style) # Connect to handler
        toolbar.addWidget(mw.penStyleComboBox)

    def add_pen_cap_controls(self):
        mw = self.main_window; eh = mw.event_handlers; toolbar = mw.tools_toolbar
        spacer = QWidget(); spacer.setFixedWidth(10); toolbar.addWidget(spacer)
        toolbar.addWidget(QLabel("Pen Cap:"))
        mw.penCapComboBox = QComboBox()
        items = [("Round", Qt.RoundCap), ("Flat", Qt.FlatCap), ("Square", Qt.SquareCap)]
        for text, data in items: mw.penCapComboBox.addItem(text, data)
        mw.penCapComboBox.currentIndexChanged.connect(eh.update_pen_cap) # Connect to handler
        toolbar.addWidget(mw.penCapComboBox)

    def add_pen_join_controls(self):
        mw = self.main_window; eh = mw.event_handlers; toolbar = mw.tools_toolbar
        spacer = QWidget(); spacer.setFixedWidth(10); toolbar.addWidget(spacer)
        toolbar.addWidget(QLabel("Pen Join:"))
        mw.penJoinComboBox = QComboBox()
        items = [("Round", Qt.RoundJoin), ("Miter", Qt.MiterJoin), ("Bevel", Qt.BevelJoin)]
        for text, data in items: mw.penJoinComboBox.addItem(text, data)
        mw.penJoinComboBox.currentIndexChanged.connect(eh.update_pen_join) # Connect to handler
        toolbar.addWidget(mw.penJoinComboBox)

    def add_brush_style_controls(self):
        mw = self.main_window; eh = mw.event_handlers; toolbar = mw.tools_toolbar
        spacer = QWidget(); spacer.setFixedWidth(10); toolbar.addWidget(spacer)
        toolbar.addWidget(QLabel("Brush Style:"))
        mw.brushStyleComboBox = QComboBox()
        items = [("None", Qt.NoBrush), ("Fill w Sec Color", "fill_with_second_color"), ("Solid", Qt.SolidPattern),
                 ("Horizontal", Qt.HorPattern), ("Vertical", Qt.VerPattern), ("Cross", Qt.CrossPattern),
                 ("Backward Diagonal", Qt.BDiagPattern), ("Forward Diagonal", Qt.FDiagPattern),
                 ("Diagonal Cross", Qt.DiagCrossPattern), ("Dense 1", Qt.Dense1Pattern),
                 ("Dense 2", Qt.Dense2Pattern), ("Dense 3", Qt.Dense3Pattern), ("Dense 4", Qt.Dense4Pattern),
                 ("Dense 5", Qt.Dense5Pattern), ("Dense 6", Qt.Dense6Pattern), ("Dense 7", Qt.Dense7Pattern)]
                 # Gradient/Texture patterns might need special handling
                 # ("Linear Gradient", Qt.LinearGradientPattern), ("Radial Gradient", Qt.RadialGradientPattern),
                 # ("Conical Gradient", Qt.ConicalGradientPattern), ("Texture", Qt.TexturePattern)]
        for text, data in items: mw.brushStyleComboBox.addItem(text, data)
        mw.brushStyleComboBox.currentIndexChanged.connect(eh.update_brush_style) # Connect to handler
        toolbar.addWidget(mw.brushStyleComboBox)


