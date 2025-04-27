import cv2
import os
import numpy as np
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QFontDialog, QApplication
from PyQt5.QtGui import QColor, QPixmap, QImage
from image_operations import ImageOperations
from vcolorpicker import getColor
from debug_types import DebugLevel

IMAGE_FILE_FILTER = "Image Files (*.png *.jpg *.bmp *.jpeg)" # Defined here for handlers

class EventHandlers:
    def __init__(self, main_window):
        self.mw = main_window # Reference to the main window instance

    # region File Operations
    def open_image(self):
        mw = self.mw
        try:
            filename, _ = QFileDialog.getOpenFileName(mw, "Select Image", "", IMAGE_FILE_FILTER)
            if filename:
                image = ImageOperations.open_image(filename)
                if image is None:
                     mw.show_debug_info(f"Failed to load image from {filename}", DebugLevel.ERROR)
                     QMessageBox.warning(mw, "Error", f"Could not load image file: {filename}")
                     return
                mw.view.set_image(image, is_new_image=True)
                mw.adjustments.reset()
                mw.reset_sliders() # Call main window's method
                mw.view.update_view()
                mw.statusBar().showMessage(f'Opened {filename}')
                mw.show_debug_info(f"Image opened: {filename}", DebugLevel.INFO)
        except Exception as e:
            mw.statusBar().showMessage(f'Error opening image: {str(e)}')
            mw.show_debug_info(f"Error opening image: {str(e)}", DebugLevel.ERROR)
            QMessageBox.critical(mw, "Error", f"An unexpected error occurred while opening the image: {str(e)}")

    def save_image(self):
        mw = self.mw
        if mw.view.image is None:
            mw.show_debug_info("No image to save", DebugLevel.WARNING)
            QMessageBox.information(mw, "Save Image", "There is no image to save.")
            return
            
        # Ensure the scene is rendered before saving
        selected_items = mw.view.scene.selectedItems() # Preserve selection
        mw.view.render_scene_to_image()
            
        if mw.view.rendered_image is None:
            mw.show_debug_info("Image rendering failed before saving", DebugLevel.ERROR)
            QMessageBox.warning(mw, "Save Error", "Could not render the image for saving.")
            # Restore selection if needed
            # for item in selected_items: item.setSelected(True) 
            return

        filename, selected_filter = QFileDialog.getSaveFileName(mw, "Save Image", "",
                                                      "PNG Files (*.png);;JPEG Files (*.jpg *.jpeg);;BMP Files (*.bmp)")
        if filename:
            try:
                # Ensure filename has the correct extension based on filter
                name, ext = os.path.splitext(filename)
                if selected_filter.startswith("PNG") and not ext.lower() == '.png':
                    filename = name + '.png'
                elif selected_filter.startswith("JPEG") and not ext.lower() in ['.jpg', '.jpeg']:
                    filename = name + '.jpg'
                elif selected_filter.startswith("BMP") and not ext.lower() == '.bmp':
                    filename = name + '.bmp'
                    
                success = cv2.imwrite(filename, mw.view.rendered_image)
                if success:
                    mw.statusBar().showMessage(f'Saved {filename}')
                    mw.show_debug_info(f"Image saved to {filename}", DebugLevel.INFO)
                else:
                    mw.statusBar().showMessage('Failed to save image')
                    mw.show_debug_info(f"Failed to save image to {filename} (cv2.imwrite returned False)", DebugLevel.ERROR)
                    QMessageBox.warning(mw, "Save Error", f"Could not save the image to {filename}.")
            except Exception as e:
                 mw.statusBar().showMessage(f'Error saving image: {str(e)}')
                 mw.show_debug_info(f"Error saving image to {filename}: {str(e)}", DebugLevel.ERROR)
                 QMessageBox.critical(mw, "Save Error", f"An unexpected error occurred while saving the image: {str(e)}")
            finally:
                 mw.view.rendered_image = None # Clear rendered image
                 # Restore selection
                 # for item in selected_items: item.setSelected(True)

    def new_image(self):
        mw = self.mw
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()
        use_clipboard = False
        image_from_clipboard = None
        width, height = 0, 0 # Initialize width and height

        if mime_data.hasImage():
            q_image = QImage(clipboard.image())
            if not q_image.isNull():
                width, height = q_image.width(), q_image.height()
                
                # Convert QImage to numpy array (handle different formats)
                q_image = q_image.convertToFormat(QImage.Format_RGBA8888)
                buffer = q_image.bits().tobytes()
                
                try:
                    image_from_clipboard = np.frombuffer(buffer, dtype=np.uint8).reshape((height, width, 4))
                    image_from_clipboard = cv2.cvtColor(image_from_clipboard, cv2.COLOR_RGBA2BGR) # OpenCV uses BGR
                    
                    reply = QMessageBox.question(mw, 'New Image', f'Use {width}x{height} image from clipboard?',
                                                 QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.Yes)

                    if reply == QMessageBox.Cancel:
                        return # User cancelled
                    elif reply == QMessageBox.Yes:
                         use_clipboard = True
                except Exception as e:
                     mw.show_debug_info(f"Error processing clipboard image: {e}", DebugLevel.ERROR)
                     QMessageBox.warning(mw, "Clipboard Error", "Could not process the image from the clipboard.")
            else:
                 mw.show_debug_info("Clipboard contains null image data", DebugLevel.WARNING)

        if use_clipboard and image_from_clipboard is not None:
            mw.view.set_image(image_from_clipboard, is_new_image=True)
            mw.statusBar().showMessage(f'Created new {width}x{height} image from clipboard')
            mw.show_debug_info(f"New image created from clipboard ({width}x{height})", DebugLevel.INFO)
        else:
            # Default or prompt for size?
            width, height = 500, 500  # Default size
            # Add dialog to ask for dimensions? e.g., QInputDialog.getInt
            image = ImageOperations.create_new_image(width, height)
            mw.view.set_image(image, is_new_image=True)
            mw.statusBar().showMessage(f'Created new {width}x{height} image')
            mw.show_debug_info(f"New blank image created ({width}x{height})", DebugLevel.INFO)
        
        # Reset adjustments for the new image
        mw.adjustments.reset()
        mw.reset_sliders() # Call main window's method

    # endregion

    # region Flip Rotate
    def perform_flip_rotate(self):
        mw = self.mw
        if mw.flip_rotate_group:
            checked_action = mw.flip_rotate_group.checkedAction()
            if checked_action:
                action_text = checked_action.text()
                mw.show_debug_info(f"Performing action: {action_text}", DebugLevel.DEBUG)
                try:
                    if action_text == 'Flip Horizontal':
                        self.flip_image('Horizontal') # Call handler method
                    elif action_text == 'Flip Vertical':
                        self.flip_image('Vertical') # Call handler method
                    elif action_text == 'Rotate CW':
                        self.rotate_image('cw') # Call handler method
                    elif action_text == 'Rotate CCW':
                        self.rotate_image('ccw') # Call handler method
                except ValueError as e:
                     mw.show_debug_info(f"Error during flip/rotate: {e}", DebugLevel.ERROR)
                     QMessageBox.warning(mw, "Flip/Rotate Error", f"Operation failed: {e}")
            else:
                 mw.show_debug_info("No flip/rotate action selected", DebugLevel.WARNING)
        else:
             mw.show_debug_info("Flip/rotate action group not initialized", DebugLevel.ERROR)

    def flip_image(self, axis):
        mw = self.mw
        if mw.view.image is not None:
            try:
                flipped_image = ImageOperations.flip(mw.view.image, axis)
                mw.view.set_image(flipped_image)
                mw.view.update_view()
                axis_name = 'horizontally' if axis == 'Horizontal' else 'vertically'
                mw.statusBar().showMessage(f'Flipped image {axis_name}')
                mw.show_debug_info(f"Image flipped {axis_name}", DebugLevel.INFO)
                # Save state after successful operation
                mw.view.save_state()
            except Exception as e:
                 mw.show_debug_info(f"Error flipping image: {e}", DebugLevel.ERROR)
                 QMessageBox.warning(mw, "Flip Error", f"Could not flip image: {e}")
        else:
             mw.show_debug_info("Cannot flip: No image loaded", DebugLevel.WARNING)

    def rotate_image(self, direction):
        mw = self.mw
        if mw.view.image is not None:
            try:
                rotated_image = ImageOperations.rotate(mw.view.image, direction)
                mw.view.set_image(rotated_image)
                mw.view.update_view()
                direction_name = "clockwise" if direction == 'cw' else "counter-clockwise"
                mw.statusBar().showMessage(f'Rotated image {direction_name}')
                mw.show_debug_info(f"Image rotated {direction_name}", DebugLevel.INFO)
                # Save state after successful operation
                mw.view.save_state()
            except Exception as e:
                 mw.show_debug_info(f"Error rotating image: {e}", DebugLevel.ERROR)
                 QMessageBox.warning(mw, "Rotate Error", f"Could not rotate image: {e}")
        else:
             mw.show_debug_info("Cannot rotate: No image loaded", DebugLevel.WARNING)

    def update_flip_rotate_button_icon(self, action):
        mw = self.mw
        if mw.flip_rotate_button:
            mw.flip_rotate_button.setIcon(action.icon())
            action.setChecked(True) 
            mw.show_debug_info(f"Flip/rotate button icon updated to {action.text()} and action checked.", DebugLevel.DEBUG)

    # endregion

    # region Undo
    def undo(self):
        mw = self.mw
        if hasattr(mw, 'view'):
            undone = mw.view.undo()
            if undone:
                 mw.statusBar().showMessage('Undo successful')
                 mw.show_debug_info("Undo action performed", DebugLevel.INFO)
            else:
                 mw.statusBar().showMessage('Nothing to undo')
                 mw.show_debug_info("Undo action failed (stack empty?)", DebugLevel.WARNING)
    # endregion

    # region Image Processing
    def apply_adjustments(self):
        mw = self.mw
        if mw.view.original_image is not None:
             try:
                mw.view.image = mw.adjustments.apply(mw.view.original_image)
                mw.view.update_view()
                mw.show_debug_info("Adjustments applied", DebugLevel.DEBUG)
                # NOTE: Adjustments are often previewed live. Should save_state be called here?
                # Probably better to save state when the user performs another action *after* adjusting.
             except Exception as e:
                 mw.show_debug_info(f"Error applying adjustments: {e}", DebugLevel.ERROR)

    def _apply_filter(self, filter_func, success_message):
        mw = self.mw
        if mw.view.image is not None:
            try:
                processed_image = filter_func(mw.view.image)
                if processed_image is not None:
                    mw.view.set_image(processed_image) # Updates original & view
                    mw.statusBar().showMessage(success_message)
                    mw.show_debug_info(success_message, DebugLevel.INFO)
                    mw.adjustments.reset()
                    mw.reset_sliders()
                    # Save state after successful filter application
                    mw.view.save_state()
                else:
                    mw.show_debug_info(f"Filter function {filter_func.__name__} returned None", DebugLevel.ERROR)
                    QMessageBox.warning(mw, "Filter Error", "The filter could not be applied.")
            except Exception as e:
                error_msg = f"Error applying filter {filter_func.__name__}: {e}"
                mw.show_debug_info(error_msg, DebugLevel.ERROR)
                QMessageBox.critical(mw, "Filter Error", f"An error occurred: {e}")
        else:
            mw.show_debug_info("Cannot apply filter: No image loaded", DebugLevel.WARNING)
            QMessageBox.information(mw, "Filter Error", "Please load an image first.")
            
    def convert_to_gray(self):
        self._apply_filter(ImageOperations.convert_to_gray, 'Converted to grayscale')

    def convert_to_rgb(self):
        self._apply_filter(ImageOperations.convert_to_rgb, 'Converted to RGB')

    def convert_to_hsv(self):
        self._apply_filter(ImageOperations.convert_to_hsv, 'Converted to HSV')

    def convert_to_sepia(self):
        self._apply_filter(ImageOperations.convert_to_sepia, 'Applied sepia filter')

    def apply_gaussian_blur(self):
        self._apply_filter(ImageOperations.apply_gaussian_blur, 'Applied Gaussian blur')

    def apply_median_blur(self):
        self._apply_filter(ImageOperations.apply_median_blur, 'Applied Median blur')

    def equalize_histogram(self):
        self._apply_filter(ImageOperations.equalize_histogram, 'Equalized histogram')

    def reset_image(self):
        mw = self.mw
        if mw.view.initial_image is not None:
            mw.view.set_image(mw.view.initial_image.copy(), is_new_image=True)
            mw.adjustments.reset()
            mw.reset_sliders()
            mw.statusBar().showMessage('Image and adjustments reset to initial state')
            mw.show_debug_info("Image reset to initial state.", DebugLevel.INFO)
        else:
            mw.statusBar().showMessage('No initial image to reset to')
            mw.show_debug_info("Reset image called, but no initial image available.", DebugLevel.WARNING)

    # endregion

    # region Shape Tools
    def toggle_shape_tool(self):
        mw = self.mw
        if not mw.shape_tools: return
        current_index = mw.shape_tools.index(mw.view.current_tool) if mw.view.current_tool in mw.shape_tools else -1
        next_index = (current_index + 1) % len(mw.shape_tools)
        next_tool = mw.shape_tools[next_index]
        
        action_to_trigger = None
        if mw.shape_group:
            for action in mw.shape_group.actions():
                 if action.text().lower() == next_tool:
                      action_to_trigger = action
                      break
                      
        if action_to_trigger:
             action_to_trigger.trigger() 
             if mw.shape_button:
                  mw.shape_button.setIcon(action_to_trigger.icon())
        else:
            mw.show_debug_info(f"Could not find action for tool {next_tool}", DebugLevel.ERROR)

    def toggle_or_select_shape_tool(self):
        mw = self.mw
        if mw.view.current_tool in mw.shape_tools:
            self.toggle_shape_tool()
        elif mw.shape_group:
            checked_action = mw.shape_group.checkedAction()
            if checked_action:
                 self.shape_tool_changed(checked_action) 
            else:
                 first_action = mw.shape_group.actions()[0] if mw.shape_group.actions() else None
                 if first_action:
                      first_action.trigger()
                 else:
                      mw.show_debug_info("No shape tools available to select.", DebugLevel.WARNING)

    def shape_tool_changed(self, action):
        mw = self.mw
        shape_tool = action.text().lower()
        mw.view.set_tool(shape_tool)
        mw.statusBar().showMessage(f'{shape_tool.capitalize()} tool selected')
        mw.show_debug_info(f"Shape tool changed to: {shape_tool}", DebugLevel.INFO)
        self.select_other_tool() # Hide brush controls

        if shape_tool == 'pixmap':
            self.insert_pixmap()

    def update_shape_button_icon(self, action):
        mw = self.mw
        if mw.shape_button:
            mw.shape_button.setIcon(action.icon())
            mw.show_debug_info(f"Shape button icon updated to {action.text()}", DebugLevel.DEBUG)

    def shape_button_clicked(self):
        mw = self.mw
        if mw.shape_group:
            action = mw.shape_group.checkedAction()
            if action:
                self.shape_tool_changed(action)
            else:
                 mw.show_debug_info("Shape button clicked but no tool is checked.", DebugLevel.WARNING)

    def insert_pixmap(self):
        mw = self.mw
        try:
            filename, _ = QFileDialog.getOpenFileName(mw, "Select Image for Pixmap", "", IMAGE_FILE_FILTER)
            if filename:
                pixmap = QPixmap(filename)
                if pixmap.isNull():
                    mw.show_debug_info(f"Failed to load pixmap from {filename}", DebugLevel.ERROR)
                    QMessageBox.warning(mw, "Error", f"Could not load image file for pixmap: {filename}")
                    return
                    
                mw.view.pixmap_to_insert = pixmap 
                mw.show_debug_info(f"Pixmap loaded from {filename}, ready to insert.", DebugLevel.INFO)
                mw.statusBar().showMessage("Click on the image to insert the pixmap.")
                if mw.view.current_tool != 'pixmap':
                     mw.view.set_tool('pixmap') 
                     if mw.pixmap_act: mw.pixmap_act.setChecked(True)
                     
        except Exception as e:
            mw.show_debug_info(f"Error selecting pixmap: {str(e)}", DebugLevel.ERROR)
            QMessageBox.critical(mw, "Error", f"An unexpected error occurred while selecting the pixmap: {str(e)}")
            
    # endregion

    # region Tool Updates
    def update_brush_size_from_input(self):
        mw = self.mw
        if mw.brush_size_input and mw.brush_size_slider:
            try:
                new_size = int(mw.brush_size_input.text())
                mw.brush_size_slider.setValue(new_size) 
            except ValueError:
                mw.brush_size_input.setText(str(mw.brush_size_slider.value()))
                mw.show_debug_info(f"Invalid brush size input: {mw.brush_size_input.text()}", DebugLevel.WARNING)

    def update_brush_opacity_from_input(self):
        mw = self.mw
        if mw.brush_opacity_input and mw.brush_opacity_slider:
            try:
                new_opacity = int(mw.brush_opacity_input.text())
                new_opacity = max(0, min(100, new_opacity))
                mw.brush_opacity_slider.setValue(new_opacity) 
            except ValueError:
                mw.brush_opacity_input.setText(str(mw.brush_opacity_slider.value()))
                mw.show_debug_info(f"Invalid opacity input: {mw.brush_opacity_input.text()}", DebugLevel.WARNING)

    def update_pen_style(self, index):
        mw = self.mw
        if mw.penStyleComboBox:
            mw.view.pen_style = mw.penStyleComboBox.itemData(index)
            mw.show_debug_info(f"Pen style set to index {index}", DebugLevel.DEBUG)

    def update_pen_cap(self, index):
        mw = self.mw
        if mw.penCapComboBox:
            mw.view.pen_cap = mw.penCapComboBox.itemData(index)
            mw.show_debug_info(f"Pen cap set to index {index}", DebugLevel.DEBUG)

    def update_pen_join(self, index):
        mw = self.mw
        if mw.penJoinComboBox:
            mw.view.pen_join = mw.penJoinComboBox.itemData(index)
            mw.show_debug_info(f"Pen join set to index {index}", DebugLevel.DEBUG)

    def update_brush_style(self, index):
        mw = self.mw
        if mw.brushStyleComboBox:
            mw.view.brush_style = mw.brushStyleComboBox.itemData(index)
            mw.show_debug_info(f"Brush style set to index {index}", DebugLevel.DEBUG)

    def select_other_tool(self):
        mw = self.mw
        if mw.brush_size_slider: mw.brush_size_slider.setVisible(False)
        if mw.brush_size_input: mw.brush_size_input.setVisible(False)
        if mw.brush_opacity_slider: mw.brush_opacity_slider.setVisible(False)
        if mw.brush_opacity_input: mw.brush_opacity_input.setVisible(False)
        if mw.penStyleComboBox: mw.penStyleComboBox.setVisible(False)
        if mw.penCapComboBox: mw.penCapComboBox.setVisible(False)
        if mw.penJoinComboBox: mw.penJoinComboBox.setVisible(False)
        if mw.brushStyleComboBox: mw.brushStyleComboBox.setVisible(False)
        if mw.tools_toolbar:
             mw.tools_toolbar.update()
        mw.show_debug_info(f"Selected tool other than brush, hiding controls.", DebugLevel.DEBUG)

    def change_brush_size(self, size):
        mw = self.mw
        if hasattr(mw, 'view'):
            mw.view.brush_size = size
            mw.show_debug_info(f"Brush size changed to {size}", DebugLevel.DEBUG)

    def select_brush_tool(self):
        mw = self.mw
        if hasattr(mw, 'view'):
            mw.view.set_tool('brush')
            mw.show_debug_info("Brush tool selected", DebugLevel.INFO)
        if mw.ui_setup: 
             mw.ui_setup.create_tools_toolbar() # Ensure toolbar is visible
        else:
             mw.show_debug_info("UISetup not initialized, cannot create tools toolbar", DebugLevel.ERROR)
    # endregion

    # region Color Management Slots
    def choose_color(self, which_color=1):
        mw = self.mw
        if which_color == 1:
            current_color_obj = mw.current_color
        else:
            current_color_obj = mw.current_color_2
            
        old_color_tuple = (current_color_obj.red(), current_color_obj.green(), 
                          current_color_obj.blue(), current_color_obj.alpha())
        try: 
            # vcolorpicker expects alpha 0-100, Qt uses 0-255
            old_color_vcp = (old_color_tuple[0], old_color_tuple[1], old_color_tuple[2], 
                             int(round(old_color_tuple[3] * 100 / 255))) 
            color_tuple_vcp = getColor(old_color_vcp) # Returns tuple (r, g, b, alpha 0-100)
            if color_tuple_vcp:
                if which_color == 1:
                    self.set_current_color_1(color_tuple_vcp)
                else:
                    self.set_current_color_2(color_tuple_vcp)
        except Exception as e:
            mw.show_debug_info(f"Error getting color: {e}", DebugLevel.ERROR)
            QMessageBox.warning(mw, "Color Picker Error", f"Could not open color picker: {e}")
            
    def set_current_color_1(self, color):
        mw = self.mw
        if isinstance(color, tuple) and len(color) == 4:
            r, g, b, a_vcp = color # alpha is 0-100 from vcolorpicker
            alpha = int(round(a_vcp * 255 / 100))
            alpha = max(0, min(255, alpha))
            mw.current_color = QColor(int(r), int(g), int(b), alpha)
        elif isinstance(color, QColor):
            mw.current_color = color 
        else:
            mw.show_debug_info(f"Unexpected color format for color 1: {color}", DebugLevel.ERROR)
            return

        mw.update_color_preview() # Call main window's method
        mw.view.set_first_color(mw.current_color)
        mw.show_debug_info(
            f"Current color 1 set to: {mw.current_color.name()}, Alpha: {mw.current_color.alpha()}", 
            DebugLevel.INFO)

    def set_current_color_2(self, color):
        mw = self.mw
        if isinstance(color, tuple) and len(color) == 4:
            r, g, b, a_vcp = color # alpha is 0-100 from vcolorpicker
            alpha = int(round(a_vcp * 255 / 100))
            alpha = max(0, min(255, alpha))
            mw.current_color_2 = QColor(int(r), int(g), int(b), alpha)
        elif isinstance(color, QColor):
             mw.current_color_2 = color 
        else:
            mw.show_debug_info(f"Unexpected color format for color 2: {color}", DebugLevel.ERROR)
            return
            
        mw.update_color_preview_2() # Call main window's method
        mw.view.set_second_color(mw.current_color_2) 
        mw.show_debug_info(
            f"Current color 2 set to: {mw.current_color_2.name()}, Alpha: {mw.current_color_2.alpha()}", 
            DebugLevel.INFO)

    def swap_colors(self):
        mw = self.mw
        mw.view.swap_colors()
        mw.current_color, mw.current_color_2 = mw.current_color_2, mw.current_color
        mw.update_color_preview() # Call main window's method
        mw.update_color_preview_2() # Call main window's method
        mw.show_debug_info("Colors swapped", DebugLevel.DEBUG)
    # endregion

    # region Status Update Slots
    def update_zoom_status(self, zoom_level):
        self.mw.statusBar().showMessage(f'Zoom: {zoom_level:.1f}%')

    def update_color_status(self, color):
        mw = self.mw
        status_text = f'Picked color: RGB({color.red()}, {color.green()}, {color.blue()}) Alpha: {color.alpha()}'
        mw.statusBar().showMessage(status_text)
        mw.show_debug_info(status_text, DebugLevel.INFO)
        self.set_current_color_1(color) # Update primary color when eyedropper is used

    def update_font_status(self, font):
        mw = self.mw
        status_text = f'Font: {font.family()}, {font.pointSize()}pt'
        mw.statusBar().showMessage(status_text)
        mw.show_debug_info(status_text, DebugLevel.INFO)

    # endregion
    
    # region Misc Slots
    def change_font(self):
        mw = self.mw
        font, ok = QFontDialog.getFont(mw.current_font, mw, "Select Font")
        if ok:
            mw.current_font = font
            mw.view.set_font(font)
            status_text = f'Font changed to {font.family()}, {font.pointSize()}pt'
            mw.statusBar().showMessage(status_text)
            mw.show_debug_info(status_text, DebugLevel.INFO)
    # endregion


