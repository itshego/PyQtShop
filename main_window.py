
# PyQt5 imports streamlined
from PyQt5.QtWidgets import QMainWindow, QAction, QLabel, QDockWidget
from PyQt5.QtGui import QColor, QPixmap, QFont
from PyQt5.QtCore import Qt

# Local imports
from custom_graphics_view import CustomGraphicsView
from image_adjustments import ImageAdjustments
from vcolorpicker import useAlpha
from debug_types import DebugLevel
from debug_utils import DebugMessage, DebugWidget
from ui_setup import UISetup
from event_handlers import EventHandlers

IMAGE_FILE_FILTER = "Image Files (*.png *.jpg *.bmp)"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Debug features
        self.debug_mode = False
        self.debug_widget = None
        self.debug_dock = None

        # UI Elements initialized here, setup handled by UISetup
        self.tools_toolbar = None
        self.shape_button = None
        self.flip_rotate_button = None
        self.brush_size_slider = None
        self.brush_size_input = None
        self.brush_opacity_slider = None
        self.brush_opacity_input = None
        self.penStyleComboBox = None
        self.penCapComboBox = None
        self.penJoinComboBox = None
        self.brushStyleComboBox = None
        self.color_dock = None
        self.color_preview = None
        self.color_preview_2 = None
        self.r_label = QLabel("R: 000")
        self.g_label = QLabel("G: 000")
        self.b_label = QLabel("B: 000")
        
        # Action groups and actions - initialized in UISetup
        self.open_act = None
        self.save_act = None
        self.new_act = None
        self.exit_act = None
        self.flip_rotate_group = None
        self.flip_h_act = None
        self.flip_v_act = None
        self.rotate_cw_act = None
        self.rotate_ccw_act = None
        self.shape_group = None
        self.circle_act = None
        self.rectangle_act = None
        self.line_act = None
        self.path_act = None
        self.polygon_act = None
        self.pixmap_act = None
        self.gray_act = None
        self.rgb_act = None
        self.hsv_act = None
        self.sepia_act = None
        self.gaussian_blur_act = None
        self.median_blur_act = None
        self.equalize_hist_act = None
        self.brush_act = None
        self.text_act = None
        self.crop_act = None
        self.eyedropper_act = None
        self.zoom_act = None
        self.undo_act = None
        self.font_act = None
        self.move_act = None
        self.swap_colors_act = None
        self.rotate_or_flip_act = None

        self.shape_tools = ['circle', 'rectangle', 'line', 'path', 'polygon', 'pixmap']
        useAlpha(True)
        self.current_tool = None
        self.view = CustomGraphicsView()
        self.view.set_debug_mode(self.debug_mode)
        self.setCentralWidget(self.view)
        self.adjustments = ImageAdjustments()
        self.adjustment_sliders = {}
        self.current_color = QColor(Qt.black)
        self.current_color_2 = QColor(Qt.white)
        self.current_font = QFont()
        
        # Instantiate UI Setup and Event Handlers
        self.ui_setup = UISetup(self)
        self.event_handlers = EventHandlers(self)
        
        # Initialize UI (Connects actions/buttons to event_handlers via ui_setup)
        self.ui_setup.init_ui() 

        self.menuBar().setFocusPolicy(Qt.NoFocus)
        self.connect_signals()
        
        # Debug menu creation remains here
        self.create_debug_menu()
        
        # Connect debug signal from view
        self.view.debugInfo.connect(self.show_debug_info)

        self.statusBar().showMessage('Ready')
        self.show_debug_info("Application initialized.", DebugLevel.INFO)

    # region Color Management UI Updates (Remain in MainWindow)
    def update_color_preview(self):
        if self.color_preview:
            pixmap = QPixmap(60, 60)
            pixmap.fill(self.current_color)
            self.color_preview.setPixmap(pixmap)
            self.update_rgb_labels()

    def update_color_preview_2(self):
        if self.color_preview_2:
            pixmap = QPixmap(60, 60)
            pixmap.fill(self.current_color_2)
            self.color_preview_2.setPixmap(pixmap)

    def update_rgb_labels(self):
        if self.r_label and self.g_label and self.b_label:
            self.r_label.setText(f"R: {self.current_color.red():03d}")
            self.g_label.setText(f"G: {self.current_color.green():03d}")
            self.b_label.setText(f"B: {self.current_color.blue():03d}")
    # endregion

    # region Qt Event Overrides (Remain in MainWindow)
    def contextMenuEvent(self, event):
        widget = self.childAt(event.pos())
        if widget == self.flip_rotate_button and self.flip_rotate_button.menu():
            global_pos = self.mapToGlobal(event.pos())
            self.flip_rotate_button.menu().exec_(global_pos)
            event.accept()
        elif widget == self.shape_button and self.shape_button.menu():
            global_pos = self.mapToGlobal(event.pos())
            self.shape_button.menu().exec_(global_pos)
            event.accept()
        else:
            super().contextMenuEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_U and not event.isAutoRepeat():
            if self.view.current_tool in self.shape_tools:
                 if self.event_handlers: self.event_handlers.toggle_shape_tool()
            elif self.shape_group:
                 checked_action = self.shape_group.checkedAction()
                 if checked_action:
                      if self.event_handlers: self.event_handlers.shape_tool_changed(checked_action)
                 else:
                      first_action = self.shape_group.actions()[0] if self.shape_group.actions() else None
                      if first_action:
                           if self.event_handlers: self.event_handlers.shape_tool_changed(first_action)
            event.accept()
        else:
            super().keyPressEvent(event)
    # endregion

    # region Miscellaneous (Debug, Signals, Reset - Remain in MainWindow)
    def create_debug_dock(self):
        if not self.debug_mode:
            if self.debug_dock:
                 self.removeDockWidget(self.debug_dock)
                 self.debug_dock.deleteLater() 
                 self.debug_dock = None
                 self.debug_widget = None
            self.view.set_debug_mode(False)
            return
        if not self.debug_dock:
            self.view.set_debug_mode(True)
            self.debug_dock = QDockWidget("Debug Panel", self)
            self.debug_widget = DebugWidget() 
            self.debug_dock.setWidget(self.debug_widget)
            self.debug_dock.setMinimumHeight(150)
            self.debug_dock.setObjectName("DebugDockWidget") 
            self.debug_dock.setVisible(True)
            self.addDockWidget(Qt.BottomDockWidgetArea, self.debug_dock)
            self.show_debug_info("Debug panel created.", DebugLevel.INFO)
        else:
             self.debug_dock.setVisible(True)
             self.view.set_debug_mode(True)

    def show_debug_info(self, info: str, level: DebugLevel = DebugLevel.INFO):
        if self.debug_mode and self.debug_widget:
            try:
                debug_message = DebugMessage(level, info) 
                self.debug_widget.add_message(debug_message)
            except Exception as e:
                 print(f"ERROR adding debug message: {e}") 
            
    def connect_signals(self):
        # Connect signals from the view to *handler* methods
        self.view.zoomChanged.connect(self.event_handlers.update_zoom_status)
        self.view.colorPicked.connect(self.event_handlers.update_color_status)
        self.view.fontChanged.connect(self.event_handlers.update_font_status)
        # Connect undo/redo state signals if needed elsewhere (e.g., to enable/disable actions)
        # self.view.undoStateChanged.connect(self.update_undo_action_state) 
        # self.view.redoStateChanged.connect(self.update_redo_action_state)

    def create_debug_menu(self):
        debug_menu = self.menuBar().addMenu('Debug')
        toggle_debug_action = QAction('Toggle Debug Panel', self)
        toggle_debug_action.setCheckable(True)
        toggle_debug_action.setChecked(self.debug_mode)
        toggle_debug_action.setShortcut('Ctrl+D')
        toggle_debug_action.triggered.connect(self.toggle_debug_mode)
        debug_menu.addAction(toggle_debug_action)

    def toggle_debug_mode(self, enabled):
        self.debug_mode = enabled
        self.show_debug_info(f"Debug mode {'enabled' if enabled else 'disabled'}.", DebugLevel.INFO)
        self.create_debug_dock() 
        
    def reset_sliders(self):
        if hasattr(self, 'adjustment_sliders') and self.adjustment_sliders:
            for label, slider in self.adjustment_sliders.items():
                try:
                    if label == "Gamma":
                        slider.setValue(100)
                    else:
                        slider.setValue(0)
                except Exception as e:
                    self.show_debug_info(f"Error resetting slider '{label}': {e}", DebugLevel.ERROR)
            self.show_debug_info("Adjustment sliders reset.", DebugLevel.DEBUG)
        else:
             self.show_debug_info("Cannot reset sliders: 'adjustment_sliders' dictionary not found or empty.", DebugLevel.WARNING)

    # endregion

