# custom_graphics_view.py
import traceback

import numpy as np
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QRubberBand, QInputDialog, \
    QGraphicsEllipseItem, QGraphicsRectItem, QGraphicsLineItem, QGraphicsDropShadowEffect, QApplication, QMessageBox
from PyQt5.QtGui import QImage, QCursor, QPixmap, QPainter, QPainterPath, QColor, QPolygonF, QPen, QFont, QBrush
from PyQt5.QtCore import Qt, QRect, QRectF, pyqtSignal, QPointF, QPoint, QLineF, QSize, QByteArray, QBuffer
from draggable_items import (DraggableTextItem, DraggableCircleItem, DraggableRectangleItem,
                             DraggableLineItem, DraggablePathItem, DraggablePixmapItem, DraggablePolygonItem)
from line_profiler import profile
from debug_types import DebugLevel


class CustomGraphicsView(QGraphicsView): 
    zoomChanged = pyqtSignal(float)
    imageChanged = pyqtSignal()
    colorPicked = pyqtSignal(QColor)
    fontChanged = pyqtSignal(QFont)
    debugInfo = pyqtSignal(str, DebugLevel)
    undoStateChanged = pyqtSignal(bool)  # Signal emitted when undo state changes
    redoStateChanged = pyqtSignal(bool)  # Signal emitted when redo state changes

    def __init__(self, parent=None):
        super().__init__(parent)
        self._debug_enabled = False
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)

        # History list and position for undo/redo
        self.history = []
        self.current_history_index = -1
        self.max_history_size = 20  # Maximum history size

        self.previous_cursor = None
        self.previous_tool = None

        self.image = None
        self.original_image = None
        self.initial_image = None
        self.rendered_image = None
        self.pixmap = None
        self.pixmap_item = None
        self.temp_pixmap_item = None
        self.is_temp_drawing = False
        self.painter = None
        self.is_drawing = False

        self.zoom_start_pos = None
        self.zoom_base_factor = 1.0
        self.zoom_current_pos = None

        self.is_zooming = False
        self.zoom_factor = 1.0
        self.min_zoom = 0.0025
        self.max_zoom = 200.0

        self.rubberband = None
        self.rubberband_origin = None
        self.crop_start = None
        self.polygon_points = None
        self.path = None

        self.start_pos = None
        self.current_shape_item = None
        self.current_tool = None
        self.current_font = QFont()
        self.text_color = QColor(Qt.black)
        self.first_color = QColor(Qt.black)
        self.second_color = QColor(Qt.white)

        self.pen_style = Qt.SolidLine
        self.pen_cap = Qt.RoundCap
        self.pen_join = Qt.RoundJoin
        self.brush_style = Qt.NoBrush
        self.brush_size = 20
        self.pen = QPen(Qt.black, self.brush_size, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        self.emit_debug(f"Pen color: {self.pen.color().name()}, width: {self.pen.width()}", DebugLevel.INFO)
        self.brush_opacity = 1.0
        self.brush_preview_item = None
        self.brush_last_point = None

        self.alt_pressed = False
        self.control_pressed = False
        self.alt_left_pressed = False
        self.alt_right_pressed = False
        self.left_click_pressed = False

        self.space_pressed = False

        self.shift_pressed = False
        self.shift_left_pressed = False
        self.shift_right_pressed = False
        self.shift_start_point = None
        self.shift_direction = None

        self.previous_mouse_pos = QPoint()

        self.setMouseTracking(True)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.NoAnchor)
        self.setResizeAnchor(QGraphicsView.NoAnchor)

    def set_image(self, image, is_new_image=False):
        self.image = image
        self.original_image = image.copy()
        if is_new_image:
            self.initial_image = image.copy()
            # Reset history when a new image is loaded
            self.history = []
            self.current_history_index = -1
            self.save_state() # Save the initial state
        else:
            # For filters/rotations, don't reset history, just save state
            self.save_state()
            
        self.update_view()
        self.emit_debug(f"Image set: shape={self.image.shape}, is_new_image={is_new_image}", DebugLevel.INFO)

    def update_view(self):
        if self.image is not None:
            height, width, channel = self.image.shape
            bytes_per_line = 3 * width
            q_img = QImage(self.image.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()

            pixmap = QPixmap.fromImage(q_img)
            if self.pixmap_item is None:
                self.pixmap_item = self.scene.addPixmap(pixmap)
            else:
                self.pixmap_item.setPixmap(pixmap)

            self.scene.setSceneRect(0, 0, width, height)
            self.setScene(self.scene)
            self.emit_debug("View updated", DebugLevel.INFO)

    def set_tool(self, tool):
        self.current_tool = tool
        if tool == 'move':
            self.setCursor(Qt.ArrowCursor)
            for item in self.scene.items():
                if isinstance(item, (DraggableCircleItem, DraggableRectangleItem, DraggableTextItem, DraggableLineItem,
                                     DraggablePathItem, DraggablePixmapItem, DraggablePolygonItem)):
                    item.signal_emitter.cursorChanged.connect(self.update_cursor)
        elif tool == 'brush':
            self.setCursor(Qt.BlankCursor)
            self.show_brush_preview()
            cursor_pos = self.mapToScene(self.mapFromGlobal(QCursor.pos()))
            self.update_brush_preview(cursor_pos)
        elif tool == 'text':
            self.setCursor(Qt.IBeamCursor)
        elif tool == 'crop':
            self.setCursor(Qt.CrossCursor)
        elif tool == 'zoom':
            self.setCursor(Qt.WhatsThisCursor)
        elif tool == 'eyedropper':
            self.setCursor(Qt.ForbiddenCursor)
        elif tool in ['circle', 'rectangle', 'line', 'path', 'pixmap', 'polygon']:
            self.setCursor(Qt.CrossCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
        if tool != 'brush':
            self.hide_brush_preview()
        self.emit_debug(f"Tool set: {tool}", DebugLevel.INFO)

    def update_cursor(self, cursor_shape):
        if self.current_tool == "move":
            self.setCursor(cursor_shape)

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.zoom_at(event.pos(), factor)

    # region MousePress
    def mousePressEvent(self, event):
        try:
            if self.image is None:
                return
            self.emit_debug("mousePressEvent called", DebugLevel.INFO)
            self.left_click_pressed = True

            if self.space_pressed:
                self.setDragMode(QGraphicsView.ScrollHandDrag)
                self.setCursor(Qt.ClosedHandCursor)
                super().mousePressEvent(event)
                return
            elif self.alt_pressed and event.button() == Qt.LeftButton:
                self.alt_left_pressed = True

            elif self.alt_pressed and event.button() == Qt.RightButton:
                self.alt_right_pressed = True

            elif self.shift_pressed and event.button() == Qt.LeftButton:
                self.shift_left_pressed = True

            elif self.shift_pressed and event.button() == Qt.RightButton:
                self.shift_right_pressed = True

            pos = self.mapToScene(event.pos())
            if self.pixmap_item:
                pos = self.pixmap_item.mapFromScene(pos)

            if self.current_tool in ['circle', 'rectangle', 'line', 'path', 'pixmap', 'polygon']:
                self.start_pos = pos
                self.is_drawing = True
                self.current_shape_item = None
            elif self.current_tool == 'brush':
                if self.alt_left_pressed:
                    self.pick_color(self.mapFromGlobal(self.cursor().pos()))
                    super().mousePressEvent(event)
                    return
                if self.alt_right_pressed:
                    super().mousePressEvent(event)
                    return
                # Pen Settings
                self.pen = QPen(self.first_color, self.brush_size, self.pen_style, self.pen_cap, self.pen_join)
                if event.button() == Qt.RightButton and self.shift_right_pressed is not True:
                    pen_color = QColor(self.second_color)
                    pen_color.setAlphaF(self.brush_opacity)
                    self.pen.setColor(pen_color)
                else:  # left and so on
                    pen_color = QColor(self.first_color)
                    pen_color.setAlphaF(self.brush_opacity)
                    self.pen.setColor(pen_color)

                if self.shift_left_pressed:
                    self.shift_start_point = pos
                    self.shift_direction = None
                if self.shift_right_pressed:
                    if self.brush_last_point is not None:
                        self.draw_line_to(pos)
                self.start_drawing(pos)

            elif self.current_tool == 'text':
                self.add_text(event.pos())
            elif self.current_tool == 'crop' and event.button() == Qt.LeftButton:
                self.start_crop(event.pos())
            elif self.current_tool == 'zoom':
                self.zoom_start_pos = event.pos()
                self.zoom_last_pos = event.pos()
                self.is_zooming = True
                self.emit_debug(f"Zoom started: start_pos={self.zoom_start_pos}", DebugLevel.INFO)
            elif self.current_tool == 'eyedropper':
                self.pick_color(event.pos())
            elif self.current_tool == 'move':
                item = self.itemAt(event.pos())
                if item and isinstance(item, (DraggableCircleItem, DraggableRectangleItem, DraggableTextItem,
                                              DraggablePolygonItem, DraggablePathItem, DraggablePixmapItem,
                                              DraggableLineItem)):
                    self.setDragMode(QGraphicsView.NoDrag)
                    item.enable_dragging()
                    item.start_pos = item.pos()
                    self.emit_debug(f"Started moving item at {item.pos()}", DebugLevel.INFO)
                else:
                    self.rubberband_origin = event.pos()
                    if not self.rubberband:
                        self.rubberband = QRubberBand(QRubberBand.Rectangle, self)
                    self.rubberband.setGeometry(QRect(self.rubberband_origin, QSize()))
                    self.rubberband.show()
            super().mousePressEvent(event)
        except Exception as e:
            self.emit_debug(f"Error in mousePressEvent: {str(e)}", DebugLevel.ERROR)
            self.emit_debug(traceback.format_exc(), DebugLevel.ERROR)

    # endregion
    # region MouseMove
    def mouseMoveEvent(self, event):
        if self.image is None:
            return

        if self.space_pressed:
            super().mouseMoveEvent(event)
            return

        elif self.alt_right_pressed:
            delta_x = event.pos().x() - self.previous_mouse_pos.x()
            # delta_y = event.pos().y() - self.previous_mouse_pos.y()

            if delta_x > 0:  # Right-side movement
                self.adjust_brush_size(1)
            elif delta_x < 0:  # Left-side movement
                self.adjust_brush_size(-1)
            self.emit_debug(f"Brush Size: {self.brush_size}", DebugLevel.INFO)
            self.previous_mouse_pos = event.pos()

        pos = self.mapToScene(event.pos())
        if self.pixmap_item:
            pos = self.pixmap_item.mapFromScene(pos)
        if self.current_tool == 'brush':
            self.update_brush_preview(self.mapToScene(event.pos()))

        if self.is_drawing:
            if self.current_tool == 'circle':
                self.update_circle(self.start_pos, pos)
            elif self.current_tool == 'rectangle':
                self.update_rectangle(self.start_pos, pos)
            elif self.current_tool == 'line':
                self.update_line(self.start_pos, pos)
            elif self.current_tool == 'path':
                self.update_path(pos)
            elif self.current_tool == 'polygon':
                self.update_polygon(pos)

            elif self.current_tool == 'brush':
                if self.shift_left_pressed:
                    self.draw_shift_left_line(pos)
                elif event.buttons() & Qt.LeftButton or Qt.RightButton:
                    self.draw_line_to(pos)
        elif self.current_tool == 'crop' and self.rubberband and not self.rubberband.isHidden():
            self.update_rubberband(event.pos())

        elif self.current_tool == 'zoom' and self.is_zooming:
            delta_x = event.pos().x() - self.zoom_last_pos.x()
            zoom_factor = 1 + (delta_x / 100)
            self.zoom_at(self.zoom_start_pos, zoom_factor)
            self.zoom_last_pos = event.pos()

        elif self.current_tool == 'move' and self.rubberband and self.rubberband_origin:
            self.rubberband.setGeometry(QRect(self.rubberband_origin, event.pos()).normalized())

            # Check Rubberband
            scene_rect = QRectF(self.mapToScene(self.rubberband.geometry().topLeft()),
                                self.mapToScene(self.rubberband.geometry().bottomRight()))
            all_items = self.scene.items()
            for item in all_items:
                if isinstance(item, (DraggableCircleItem, DraggableRectangleItem, DraggableTextItem,
                                     DraggablePolygonItem, DraggablePathItem, DraggablePixmapItem,
                                     DraggableLineItem)):
                    if scene_rect.intersects(item.sceneBoundingRect()):
                        item.setSelected(True)
                        item.enable_dragging()
                    else:
                        item.setSelected(False)
                        item.disable_dragging()
        else:
            super().mouseMoveEvent(event)

    # endregion
    # region MouseRelease
    def mouseReleaseEvent(self, event):
        try:
            if self.image is None:
                return
            self.emit_debug("mouseReleaseEvent called", DebugLevel.INFO)
            if not self.left_click_pressed:
                self.emit_debug("U R CLICKIN' WAY TOO FAST BRO!", DebugLevel.WARNING)
                self.mousePressEvent(event)

            if self.space_pressed:
                self.setDragMode(QGraphicsView.NoDrag)
                self.setCursor(Qt.OpenHandCursor)
                super().mouseReleaseEvent(event)
                return

            pos = self.mapToScene(event.pos())
            if self.pixmap_item:
                pos = self.pixmap_item.mapFromScene(pos)

            if self.is_drawing:
                self.is_drawing = False
                if self.current_tool == 'brush':
                    self.end_drawing()
                elif self.current_tool == 'circle':
                    self.finish_circle(self.start_pos, pos)
                elif self.current_tool == 'rectangle':
                    self.finish_rectangle(self.start_pos, pos)
                elif self.current_tool == 'line':
                    self.finish_line(self.start_pos, pos)
                elif self.current_tool == 'path':
                    self.finish_path()
                elif self.current_tool == 'pixmap':
                    self.add_pixmap(pos)
                elif self.current_tool == 'polygon':
                    self.finish_polygon()
                self.start_pos = None
                self.current_shape_item = None
            elif self.current_tool == 'crop' and event.button() == Qt.LeftButton:
                self.end_crop(event.pos())
            elif self.current_tool == 'zoom':
                self.emit_debug(f"Zoom release: start_pos={self.zoom_start_pos}, current_pos={event.pos()}", DebugLevel.INFO)
                if self.zoom_start_pos is not None:
                    distance = QPoint(event.pos() - self.zoom_start_pos).manhattanLength()
                    if distance <= 5:  # 5 pixel tolerance
                        factor = 1.2 if event.button() == Qt.LeftButton else 1 / 1.2
                        self.zoom_at(event.pos(), factor)
                    else:
                        self.emit_debug("Zoom cancelled due to large distance", DebugLevel.WARNING)
                else:
                    self.emit_debug("Zoom cancelled: start_pos is None", DebugLevel.WARNING)
                self.zoom_start_pos = None
                self.zoom_last_pos = None
                self.is_zooming = False
            elif self.current_tool == 'move':
                if self.rubberband:
                    self.rubberband.hide()
                    self.rubberband = None
                    self.rubberband_origin = None
                else:
                    item = self.itemAt(event.pos())
                    if item and isinstance(item, (DraggableCircleItem, DraggableRectangleItem, DraggableTextItem,
                                                  DraggablePolygonItem, DraggablePathItem, DraggablePixmapItem,
                                                  DraggableLineItem)):
                        if hasattr(item, 'start_pos'):
                            delta = item.pos() - item.start_pos
                            item.setPos(item.start_pos + delta)
                            self.emit_debug(f"Finished moving item to {item.pos()}", DebugLevel.INFO)
                            delattr(item, 'start_pos')
                            
                            # Save state after moving the item
                            self.save_state()
                self.setDragMode(QGraphicsView.NoDrag)

            self.alt_left_pressed = False
            self.alt_right_pressed = False
            self.shift_left_pressed = False
            self.shift_right_pressed = False
            self.left_click_pressed = False
            super().mouseReleaseEvent(event)
        except Exception as e:
            self.emit_debug(f"Error in mouseReleaseEvent: {str(e)}", DebugLevel.ERROR)
            self.emit_debug(traceback.format_exc(), DebugLevel.ERROR)

    # endregion
    # region Keyboard

    def keyPressEvent(self, event):
        try:
            if event.key() == Qt.Key_Shift and not event.isAutoRepeat():
                self.shift_pressed = True
            elif event.key() == Qt.Key_Alt and not event.isAutoRepeat():
                self.alt_pressed = True
            elif event.key() == Qt.Key_Control and not event.isAutoRepeat():
                self.control_pressed = True
            elif event.key() == Qt.Key_Space and not event.isAutoRepeat():
                self.space_pressed = True
                self.previous_tool = self.current_tool
                self.previous_cursor = self.cursor()
                self.hide_brush_preview()
                self.setDragMode(QGraphicsView.ScrollHandDrag)
                self.setCursor(Qt.OpenHandCursor)
                if self.rubberband:
                    self.rubberband.hide()
            elif event.key() == Qt.Key_Delete:
                for item in self.scene.selectedItems():
                    if isinstance(item, (DraggableCircleItem, DraggableRectangleItem, DraggableTextItem,
                                         DraggableLineItem, DraggablePathItem, DraggablePixmapItem,
                                         DraggablePolygonItem)):
                        self.scene.removeItem(item)
                        self.emit_debug(f"Deleted item: {item}", DebugLevel.INFO)
            elif self.control_pressed:
                if event.key() == Qt.Key_V and not event.isAutoRepeat():
                    if self.paste_image_from_clipboard():
                        # Save state after successful paste
                        self.save_state()
                elif event.key() == Qt.Key_Z and not event.isAutoRepeat():
                    self.undo()
                    return
                elif event.key() == Qt.Key_Y and not event.isAutoRepeat():
                    self.redo()
                    return
            super().keyPressEvent(event)
        except Exception as e:
            self.emit_debug(f"Error in keyPressEvent: {str(e)}", DebugLevel.ERROR)
            self.emit_debug(traceback.format_exc(), DebugLevel.ERROR)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Shift and not event.isAutoRepeat():
            self.shift_pressed = False
        elif event.key() == Qt.Key_Alt and not event.isAutoRepeat():
            self.alt_pressed = False
        elif event.key() == Qt.Key_Control and not event.isAutoRepeat():
            self.control_pressed = False
        elif event.key() == Qt.Key_Space and not event.isAutoRepeat():
            self.space_pressed = False
            self.setDragMode(QGraphicsView.NoDrag)
            self.setCursor(self.previous_cursor)
            self.set_tool(self.previous_tool)
        super().keyReleaseEvent(event)

    # endregion
    # region Crop Functions

    def start_crop(self, pos):
        if not self.rubberband:
            self.rubberband = QRubberBand(QRubberBand.Rectangle, self.viewport())
        self.crop_start = self.map_to_image(pos)
        mapped_pos = self.map_from_image(self.crop_start)
        self.rubberband.setGeometry(QRectF(mapped_pos, mapped_pos).toRect())
        self.rubberband.show()
        self.emit_debug(f"Crop started: view_pos={pos}, image_pos={self.crop_start}", DebugLevel.INFO)

    def update_rubberband(self, pos):
        if self.rubberband:
            end = self.map_to_image(pos)
            rect = QRectF(self.crop_start, end).normalized()
            mapped_rect = QRectF(self.map_from_image(rect.topLeft()),
                                 self.map_from_image(rect.bottomRight())).normalized()
            self.rubberband.setGeometry(mapped_rect.toRect())
            self.emit_debug(f"Rubberband updated: view_pos={pos}, image_pos={end}, rect={rect}, "
                                f"mapped_rect={mapped_rect}", DebugLevel.INFO)

    def end_crop(self, pos):
        if self.rubberband:
            self.rubberband.hide()
            end_image = self.map_to_image(pos)
            self.emit_debug(f"Crop ended: view_pos={pos}, start={self.crop_start}, end={end_image}", DebugLevel.INFO)
            self.crop_image()

    def crop_image(self):
        if self.image is None or not self.rubberband:
            self.emit_debug("Crop cancelled: No image or rubberband", DebugLevel.WARNING)
            return

        # Get rubberband geometry in viewport coordinates
        viewport_rect = self.rubberband.geometry()

        # Map viewport rectangle corners to scene coordinates
        # Ensure we use QPointF for potentially fractional coordinates
        top_left_scene = self.mapToScene(viewport_rect.topLeft())
        bottom_right_scene = self.mapToScene(viewport_rect.bottomRight())
        scene_rect = QRectF(top_left_scene, bottom_right_scene).normalized()

        # Get image boundaries in scene coordinates (usually 0,0 to width,height)
        if self.pixmap_item:
            image_scene_rect = self.pixmap_item.sceneBoundingRect()
        else:
            # Fallback if pixmap_item doesn't exist (shouldn't happen if image is set)
            self.emit_debug("Crop warning: No pixmap_item found, using scene rect.", DebugLevel.WARNING)
            image_scene_rect = self.scene.sceneRect() # Use scene rect as approx image boundary

        # Intersect the selection rectangle with the image rectangle in scene coordinates
        # This clamps the selection to the visible image area in the scene
        crop_scene_rect = scene_rect.intersected(image_scene_rect)

        if crop_scene_rect.isEmpty() or crop_scene_rect.width() <= 0 or crop_scene_rect.height() <= 0:
             self.emit_debug(f"Crop cancelled: Invalid scene crop rect {crop_scene_rect}", DebugLevel.WARNING)
             return

        # Now, map the valid crop rectangle *from scene coordinates* back to *image pixel coordinates*.
        # If there's a pixmap_item, its coordinate system is effectively the image's pixel system.
        if self.pixmap_item:
            # Map the clamped scene rectangle to the pixmap item's coordinate system (image pixels)
            # Note: mapFromScene returns a QPolygonF, get its bounding rect
            image_crop_rect = self.pixmap_item.mapFromScene(crop_scene_rect).boundingRect()
        else:
            # If no pixmap item, assume scene coordinates directly map to image pixels (no scaling/offset)
            # This case might be less accurate if transforms were applied without a pixmap_item
             image_crop_rect = crop_scene_rect # Approximate

        # Convert QRectF coordinates to integer pixel indices for slicing
        x = int(round(image_crop_rect.left()))
        y = int(round(image_crop_rect.top()))
        w = int(round(image_crop_rect.width()))
        h = int(round(image_crop_rect.height()))

        # Final boundary check against the actual image dimensions AFTER mapping to pixels
        img_height, img_width = self.image.shape[:2]
        x = max(0, x)
        y = max(0, y)
        # Ensure x+w and y+h do not exceed image bounds
        w = min(w, img_width - x)
        h = min(h, img_height - y)

        # Final check for valid dimensions
        if w <= 0 or h <= 0:
            self.emit_debug(f"Crop cancelled: Invalid pixel crop dimensions x={x}, y={y}, w={w}, h={h}", DebugLevel.WARNING)
            return

        self.emit_debug(f"Cropping image pixels: x={x}, y={y}, w={w}, h={h}", DebugLevel.INFO)

        try:
            # Perform the crop using numpy slicing on the *current* image
            cropped_img = self.image[y:y + h, x:x + w].copy()

            if cropped_img.size == 0:
                 self.emit_debug("Crop resulted in an empty image.", DebugLevel.ERROR)
                 QMessageBox.warning(self, "Crop Error", "Crop resulted in an empty image.")
                 return

            # Update the image and view using set_image
            self.set_image(cropped_img) # Updates original_image, pixmap_item, and view
            self.save_state() # Save the new cropped state
            self.emit_debug("Image cropped successfully", DebugLevel.INFO)

        except Exception as e:
            self.emit_debug(f"Error during cropping slice/update: {e}\n{traceback.format_exc()}", DebugLevel.ERROR)
            QMessageBox.critical(self, "Crop Error", f"An error occurred during cropping: {e}")
        finally:
            # Reset rubberband state
            self.rubberband_origin = None
            # Keep rubberband instance but hide it
            # self.rubberband.hide() # Already hidden in end_crop

    # endregion
    # region Brush

    def show_brush_preview(self):
        if self.brush_preview_item is None:
            self.brush_preview_item = QGraphicsEllipseItem(0, 0, self.brush_size, self.brush_size)
            self.brush_preview_item.setPen(QPen(Qt.black, 1))
            preview_color = QColor(self.first_color)
            preview_alpha = int(self.brush_opacity * 255 * 0.31)
            preview_color.setAlpha(preview_alpha)
            self.brush_preview_item.setBrush(preview_color)
            self.brush_preview_item.setZValue(self.pixmap_item.zValue() + 2)
            # White glow effect
            glow = QGraphicsDropShadowEffect()
            glow.setColor(QColor(255, 255, 255, 255))
            glow.setBlurRadius(2)
            glow.setOffset(0, 0)

            self.brush_preview_item.setGraphicsEffect(glow)
            self.scene.addItem(self.brush_preview_item)
        else:
            self.brush_preview_item.show()

    def hide_brush_preview(self):
        if self.brush_preview_item is not None:
            self.brush_preview_item.hide()

    def update_brush_preview(self, pos):
        if self.brush_preview_item:
            radius = self.brush_size / 2
            self.brush_preview_item.setRect(pos.x() - radius, pos.y() - radius, self.brush_size, self.brush_size)

    def start_drawing(self, pos):
        self.is_drawing = True
        self.brush_last_point = pos
        self.emit_debug(f"Started drawing at {pos}", DebugLevel.INFO)

    def draw_shift_left_line(self, end_point):
        dx = end_point.x() - self.shift_start_point.x()
        dy = end_point.y() - self.shift_start_point.y()

        if self.shift_direction is None:
            if abs(dx) > abs(dy):
                self.shift_direction = 'horizontal'
            else:
                self.shift_direction = 'vertical'

        if self.shift_direction == 'horizontal':
            end_point.setY(self.shift_start_point.y())
        elif self.shift_direction == 'vertical':
            end_point.setX(self.shift_start_point.x())

        self.draw_line_to(end_point)

    def draw_line_to(self, end_point):
        # start_time = time.time()
        if self.image is None or self.brush_last_point is None:
            return
        if self.brush_last_point != end_point:  # Only draw if points are different
            # Tho brush_last_point shouldn't be same with end_point, since this only works when mouse moves.
            # This might work on shift press situations.
            scene_line = QLineF(self.brush_last_point, end_point)
            line_item = self.scene.addLine(scene_line, self.pen)
            self.emit_debug(f"Line added to scene: {scene_line.p1()} to {scene_line.p2()}", DebugLevel.INFO)
            self.brush_last_point = end_point
            # self.emit_debug(f"Drew line to {end_point}")
        else:
            self.emit_debug("Skipped drawing line (same start and end points)", DebugLevel.WARNING)

        # end_time = time.time()
        # execution_time = end_time - start_time
        # self.emit_debug(f"draw_line_to execution time: {execution_time:.4f} seconds", DebugLevel.DEBUG)

    def end_drawing(self):
        if self.is_drawing:
            self.shift_start_point = None
            self.shift_direction = None
            
            # Çizim öncesi durumu kaydet
            self.save_state()
            
            pixmap = self.pixmap_item.pixmap()
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing, True)

            for item in self.scene.items():
                if isinstance(item, QGraphicsLineItem):
                    line = item.line()
                    painter.setPen(item.pen())
                    painter.drawLine(line)
                    self.scene.removeItem(item)

            painter.end()
            self.pixmap_item.setPixmap(pixmap)
            self.scene.update()
            self.update_image_from_pixmap()
            
            self.emit_debug("Drawing ended and applied to pixmap", DebugLevel.INFO)

    def update_image_from_pixmap(self):
        if self.pixmap_item is not None:
            pixmap = self.pixmap_item.pixmap()
            image = pixmap.toImage()
            self.image = self.qImage_to_numpy(image)

    @staticmethod
    def qImage_to_numpy(q_image):
        width = q_image.width()
        height = q_image.height()
        ptr = q_image.constBits()
        ptr.setsize(height * width * 4)
        arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 4))
        return arr[:, :, :3]

    # endregion
    # region Shapes

    def add_text(self, pos):
        if self.current_tool == 'text':
            try:
                text, ok = QInputDialog.getText(self, "Add Text", "Enter text:")
                if ok and text:
                    text_item = DraggableTextItem(text)
                    text_item.setFont(self.current_font)
                    text_item.setDefaultTextColor(self.text_color)
                    scene_pos = self.mapToScene(pos)
                    text_item.setPos(scene_pos)
                    text_item.setZValue(self.pixmap_item.zValue() + 1)
                    self.scene.addItem(text_item)
                    self.scene.clearSelection()
                    text_item.setSelected(True)
                    
                    # Save the current state after adding text
                    self.save_state()

                    self.emit_debug(f"Text added at {scene_pos}", DebugLevel.INFO)
            except Exception as e:
                self.emit_debug(f"Error adding text: {str(e)}", DebugLevel.ERROR)
                self.emit_debug(traceback.format_exc(), DebugLevel.ERROR)

    def add_pixmap(self, pos):
        if self.current_tool == 'pixmap':
            try:
                if self.pixmap is None:
                    self.emit_debug("No pixmap to add", DebugLevel.WARNING)
                    return
                # Save state before adding pixmap
                # NOTE: Currently disabling undo for pixmap
                # self.save_state()
                pixmap_item = DraggablePixmapItem(self.pixmap)
                pixmap_item.setPos(pos)
                pixmap_item.setZValue(self.pixmap_item.zValue() + 1)
                self.scene.addItem(pixmap_item)
                self.emit_debug(f"Pixmap inserted at ({pos.x()}, {pos.y()})", DebugLevel.INFO)
            except Exception as e:
                self.emit_debug(f"Error adding pixmap: {str(e)}", DebugLevel.ERROR)
                self.emit_debug(traceback.format_exc(), DebugLevel.ERROR)

    def update_circle(self, start, end):
        if self.current_shape_item:
            self.scene.removeItem(self.current_shape_item)
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        if self.shift_pressed:  # Circle
            radius = (dx ** 2 + dy ** 2) ** 0.5
            self.current_shape_item = QGraphicsEllipseItem(start.x() - radius, start.y() - radius, radius * 2,
                                                           radius * 2)
        else:  # Ellipse
            width = abs(dx) * 2
            height = abs(dy) * 2
            self.current_shape_item = QGraphicsEllipseItem(start.x() - width / 2, start.y() - height / 2, width, height)

        self.current_shape_item.setPen(QPen(Qt.black, 2))
        self.scene.addItem(self.current_shape_item)

    def finish_circle(self, start, end):
        try:
            if self.current_shape_item:
                self.scene.removeItem(self.current_shape_item)
            dx = end.x() - start.x()
            dy = end.y() - start.y()
            if self.shift_pressed:  # Circle

                radius = (dx ** 2 + dy ** 2) ** 0.5
                circle = DraggableCircleItem(0, 0, radius * 2, radius * 2)
                circle.setPos(start.x() - radius, start.y() - radius)
            else:  # Ellipse
                width = abs(dx) * 2
                height = abs(dy) * 2
                circle = DraggableCircleItem(0, 0, width, height)
                circle.setPos(start.x() - width / 2, start.y() - height / 2)

            circle.setPen(QPen(self.first_color, self.brush_size, self.pen_style, self.pen_cap, self.pen_join))
            if self.brush_style != Qt.NoBrush:
                if self.brush_style == "fill_with_second_color":
                    circle.setBrush(QBrush(self.second_color))
                else:
                    circle.setBrush(QBrush(self.first_color, self.brush_style))
            else:
                # Explicitly set an empty brush
                circle.setBrush(QBrush())
            
            self.scene.addItem(circle)
            
            # Save the current state after adding the shape
            self.save_state()
            
            self.emit_debug(f"{'Circle' if self.shift_pressed else 'Ellipse'} added at ({start.x()}, {start.y()})", DebugLevel.INFO)
        except Exception as e:
            self.emit_debug(f"Error adding {'circle' if self.shift_pressed else 'ellipse'}: {str(e)}", DebugLevel.ERROR)
            self.emit_debug(traceback.format_exc(), DebugLevel.ERROR)

    def update_rectangle(self, start, end):
        if self.current_shape_item:
            self.scene.removeItem(self.current_shape_item)

        if self.shift_pressed:  # Square
            side = min(abs(end.x() - start.x()), abs(end.y() - start.y()))
            rect = QRectF(start.x(), start.y(), side, side)
        else:  # Rectangle
            rect = QRectF(start, end).normalized()

        self.current_shape_item = QGraphicsRectItem(rect)
        self.current_shape_item.setPen(QPen(Qt.black, 2))
        self.scene.addItem(self.current_shape_item)

    def finish_rectangle(self, start, end):
        try:
            if self.current_shape_item:
                self.scene.removeItem(self.current_shape_item)
            
            if self.shift_pressed:  # Square
                side = min(abs(end.x() - start.x()), abs(end.y() - start.y()))
                rect = QRectF(start.x(), start.y(), side, side)
            else:  # Rectangle
                rect = QRectF(start, end).normalized()

            rectangle = DraggableRectangleItem(0, 0, rect.width(), rect.height())
            rectangle.setPen(QPen(self.first_color, self.brush_size, self.pen_style, self.pen_cap, self.pen_join))
            if self.brush_style != Qt.NoBrush:
                if self.brush_style == "fill_with_second_color":
                    rectangle.setBrush(QBrush(self.second_color))
                else:
                    rectangle.setBrush(QBrush(self.first_color, self.brush_style))
            else:
                # Explicitly set an empty brush
                rectangle.setBrush(QBrush())
            
            rectangle.setPos(rect.topLeft())
            self.scene.addItem(rectangle)
            
            # Save the current state after adding the shape
            self.save_state()
            
            self.emit_debug(f"{'Square' if self.shift_pressed else 'Rectangle'} added at ({start.x()}, {start.y()})", DebugLevel.INFO)
        except Exception as e:
            self.emit_debug(f"Error adding {'square' if self.shift_pressed else 'rectangle'}: {str(e)}", DebugLevel.ERROR)
            self.emit_debug(traceback.format_exc(), DebugLevel.ERROR)

    def update_line(self, start, end):
        if self.current_shape_item:
            self.scene.removeItem(self.current_shape_item)
        self.current_shape_item = QGraphicsLineItem(start.x(), start.y(), end.x(), end.y())
        self.current_shape_item.setPen(QPen(Qt.black, 2))
        self.scene.addItem(self.current_shape_item)

    def finish_line(self, start, end):
        try:
            if self.current_shape_item:
                self.scene.removeItem(self.current_shape_item)
            line = DraggableLineItem(0, 0, end.x() - start.x(), end.y() - start.y())
            line.setPen(QPen(self.first_color, self.brush_size, self.pen_style, self.pen_cap, self.pen_join))
            line.setPos(start.x(), start.y())
            self.scene.addItem(line)
            
            # Save the current state after adding the line
            self.save_state()
            
            self.emit_debug(f"Line added from ({start.x()}, {start.y()}) to ({end.x()}, {end.y()})", DebugLevel.INFO)
        except Exception as e:
            self.emit_debug(f"Error adding line: {str(e)}", DebugLevel.ERROR)
            self.emit_debug(traceback.format_exc(), DebugLevel.ERROR)

    def update_path(self, point):
        if self.path is None:
            self.path = QPainterPath(self.start_pos)
        self.path.lineTo(point)
        if self.current_shape_item:
            self.scene.removeItem(self.current_shape_item)
        self.current_shape_item = self.scene.addPath(self.path, self.pen)

    def finish_path(self):
        try:
            if self.current_shape_item:
                self.scene.removeItem(self.current_shape_item)
            if self.path is None:
                self.emit_debug(f"Error adding Path: You should drag the mouse without releasing it to create a path.", DebugLevel.WARNING)
                return
            bounding_rect = self.path.boundingRect()
            translated_path = QPainterPath(self.path)
            translated_path.translate(-bounding_rect.topLeft())
            path_item = DraggablePathItem(translated_path)
            path_item.setPen(self.pen)
            path_item.setPos(bounding_rect.topLeft())
            self.scene.addItem(path_item)
            
            # Save the current state after adding the path
            # NOTE: Currently disabling undo for path
            # self.save_state()
            
            self.emit_debug("Path added successfully", DebugLevel.INFO)
            self.path = None
        except Exception as e:
            self.emit_debug(f"Error adding path: {str(e)}", DebugLevel.ERROR)
            self.emit_debug(traceback.format_exc(), DebugLevel.ERROR)

    def update_polygon(self, point):
        self.polygon_points.append(point)
        if self.current_shape_item:
            self.scene.removeItem(self.current_shape_item)
        polygon = QPolygonF(self.polygon_points)
        self.current_shape_item = self.scene.addPolygon(polygon, self.pen)

    def finish_polygon(self):
        try:
            if self.current_shape_item:
                self.scene.removeItem(self.current_shape_item)
            
            points = [point for point in self.polygon_points]
            if len(points) < 3:
                self.emit_debug(f"Error adding Polygon: Not enough points ({len(points)}). Minimum 3 required.", DebugLevel.WARNING)
                return
            
            polygon = QPolygonF(points)
            polygon_item = DraggablePolygonItem(polygon)
            polygon_item.setPen(QPen(self.first_color, self.brush_size, self.pen_style, self.pen_cap, self.pen_join))
            
            if self.brush_style != Qt.NoBrush:
                if self.brush_style == "fill_with_second_color":
                    polygon_item.setBrush(QBrush(self.second_color))
                else:
                    polygon_item.setBrush(QBrush(self.first_color, self.brush_style))
            else:
                polygon_item.setBrush(QBrush())
            
            self.scene.addItem(polygon_item)
            self.polygon_points = []
            
            # Save the current state after adding the polygon
            # NOTE: Currently disabling undo for polygon
            # self.save_state()
            
            self.emit_debug(f"Polygon added with {len(points)} points", DebugLevel.INFO)
        except Exception as e:
            self.emit_debug(f"Error adding polygon: {str(e)}", DebugLevel.ERROR)
            self.emit_debug(traceback.format_exc(), DebugLevel.ERROR)

    # endregion
    # region smth
    @profile
    def zoom_at(self, pos, factor):
        self.emit_debug(f"zoom_at called", DebugLevel.INFO)
        old_pos = self.mapToScene(pos)
        self.scale(factor, factor)
        new_pos = self.mapToScene(pos)

        delta = new_pos - old_pos
        self.translate(delta.x(), delta.y())

        new_zoom = self.zoom_factor * factor
        if self.min_zoom <= new_zoom <= self.max_zoom:
            self.zoom_factor = new_zoom
            self.update_scene_rect()
            self.zoomChanged.emit(self.zoom_factor * 100)
        else:
            # Restoring
            self.scale(1 / factor, 1 / factor)

    def update_scene_rect(self):
        visible_rect = self.mapToScene(self.viewport().rect()).boundingRect()
        image_rect = self.pixmap_item.boundingRect()

        # When it's over 500%
        if self.zoom_factor >= 5:
            margin = 800  # Pixel but it wil be divided by zoom factor.
            new_width = image_rect.width() + margin / self.zoom_factor
            new_height = image_rect.height() + margin / self.zoom_factor
        else:
            max_scene_width = image_rect.width() * 1.8
            max_scene_height = image_rect.height() * 1.8

            min_scene_width = image_rect.width() * 1.1
            min_scene_height = image_rect.height() * 1.1

            new_width = max(min_scene_width, min(max_scene_width, visible_rect.width() / self.zoom_factor))
            new_height = max(min_scene_height, min(max_scene_height, visible_rect.height() / self.zoom_factor))

        center_x = image_rect.center().x()
        center_y = image_rect.center().y()

        new_rect = QRectF(
            center_x - new_width / 2,
            center_y - new_height / 2,
            new_width,
            new_height
        )

        self.setSceneRect(new_rect)
        self.emit_debug(f"Scene rect updated: {new_rect}, Zoom: {self.zoom_factor}", DebugLevel.INFO)

    def reset_zoom(self):
        if self.image is not None:
            self.resetTransform()
            # self.scale(self.scale_factor, self.scale_factor)  # Fit image to the window
            self.zoom_factor = 1.0
            self.zoomChanged.emit(self.zoom_factor * 100)
            self.emit_debug(f"Zoom reset: zoom_factor={self.zoom_factor}", DebugLevel.INFO)

    def reset_image(self):
        if self.original_image is not None:
            self.set_image(self.original_image.copy())

    def get_image(self):
        return self.image

    def pick_color(self, pos):
        scene_pos = self.mapToScene(pos)
        if self.pixmap_item:
            pixel_color = self.pixmap_item.pixmap().toImage().pixelColor(int(scene_pos.x()), int(scene_pos.y()))
            self.colorPicked.emit(pixel_color)
            self.emit_debug(f"Color picked: RGB({pixel_color.red()}, {pixel_color.green()}, {pixel_color.blue()})", DebugLevel.INFO)

    def swap_colors(self):
        temp = self.first_color
        self.first_color, self.text_color = self.second_color, self.second_color
        self.second_color = temp
        self.emit_debug(f"Colors swapped: First={self.first_color.name()}, Second={self.second_color.name()}", DebugLevel.INFO)

    def paste_image_from_clipboard(self):
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()

        if mime_data.hasImage():
            image = QImage(mime_data.imageData())
            pixmap = QPixmap.fromImage(image)

            view_center = self.mapToScene(self.viewport().rect().center())
            pixmap_center = QPointF(pixmap.width() / 2, pixmap.height() / 2)
            pos = view_center - pixmap_center

            pixmap_item = DraggablePixmapItem(pixmap)
            pixmap_item.setPos(pos)
            self.scene.addItem(pixmap_item)

            self.emit_debug(f"Pixmap pasted at ({pos.x()}, {pos.y()})", DebugLevel.INFO)
            return True
        return False

    # endregion
    # region Sets

    def set_font(self, font):
        self.current_font = font
        self.fontChanged.emit(font)

    def set_text_color(self, color):
        self.text_color = color
        self.emit_debug(f"Text color set to: {color.name()}", DebugLevel.INFO)

    def set_first_color(self, color):
        self.first_color = color
        self.emit_debug(f"First color/Brush set to: {color.name()}", DebugLevel.INFO)
        if self.brush_preview_item:
            preview_color = QColor(color)
            preview_alpha = int(self.brush_opacity * 255 * 0.31)  # 255 * 0.31 ~= 80
            preview_color.setAlpha(preview_alpha)
            self.brush_preview_item.setBrush(preview_color)

    def set_second_color(self, color):
        self.second_color = color
        self.emit_debug(f"Second color/Fill set to: {color.name()}", DebugLevel.INFO)

    def set_brush_opacity(self, opacity):
        self.brush_opacity = opacity / 100.0
        self.emit_debug(f"Brush opacity set to: {self.brush_opacity}", DebugLevel.INFO)
        if self.brush_preview_item:
            preview_color = QColor(self.first_color)
            preview_alpha = int(self.brush_opacity * 255 * 0.31)
            preview_color.setAlpha(preview_alpha)
            self.brush_preview_item.setBrush(preview_color)

    def set_brush_size(self, size):
        self.brush_size = size
        self.emit_debug(f"Brush size set to: {size}", DebugLevel.INFO)

    def adjust_brush_size(self, amount):
        new_size = self.brush_size + amount
        self.brush_size = max(1, min(300, new_size))
        self.emit_debug(f"Brush size set to: {self.brush_size}", DebugLevel.INFO)

    def render_scene_to_image(self):
        if self.image is None or self.pixmap_item is None:
            return

        # Delete all selected items because otherwise it'll print selection area too.
        for item in self.scene.selectedItems():
            item.setSelected(False)

        scene_rect = self.scene.sceneRect()
        width = int(scene_rect.width())
        height = int(scene_rect.height())

        qimage = QImage(width, height, QImage.Format_RGBA8888)
        qimage.fill(0)  # This one creates transparent background

        painter = QPainter(qimage)
        self.scene.render(painter, QRectF(qimage.rect()), scene_rect)
        painter.end()

        # QImage to numpy arr
        ptr = qimage.bits()
        ptr.setsize(height * width * 4)
        arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 4))

        # BGR to RGB
        arr = arr[:, :, [2, 1, 0, 3]]

        # Numpy arr to org image
        y_end = min(self.image.shape[0], arr.shape[0])
        x_end = min(self.image.shape[1], arr.shape[1])

        alpha_s = arr[:y_end, :x_end, 3] / 255.0
        alpha_l = 1.0 - alpha_s

        rendered_image = self.image.copy()
        for c in range(0, 3):
            rendered_image[:y_end, :x_end, c] = (alpha_s * arr[:y_end, :x_end, c] +
                                                 alpha_l * rendered_image[:y_end, :x_end, c]).astype(np.uint8)

        self.rendered_image = rendered_image
        self.emit_debug("Scene rendered to image", DebugLevel.INFO)

    def map_to_image(self, pos):
        view_pos = self.mapToScene(pos)
        return QPointF(view_pos.x(), view_pos.y())

    def map_from_image(self, pos):
        return self.mapFromScene(QPointF(pos.x(), pos.y()))

    # endregion

    def set_debug_mode(self, enabled: bool):
        """Sets the Debug Mode"""
        self._debug_enabled = enabled
        self.emit_debug("Debug mode " + ("enabled" if enabled else "disabled"), DebugLevel.INFO)

    def emit_debug(self, message: str, level: DebugLevel):
        """Emits debug messages if it's wanted"""
        if self._debug_enabled:
            self.debugInfo.emit(message, level)

    def smth(self):
        pass

    # region Undo/Redo Functions
    
    def save_state(self):
        """Saves the current image state to the history"""
        if self.image is None:
            self.emit_debug("save_state called but no image exists", DebugLevel.WARNING)
            return
        
        # Prepare the state including items on the scene
        items_data = []
        for item in self.scene.items():
            if isinstance(item, (DraggableCircleItem, DraggableRectangleItem, DraggableTextItem, DraggableLineItem)):
                # Save the item type and position
                item_type = type(item).__name__
                pos = item.pos()
                item_data = {
                    'type': item_type,
                    'pos': (pos.x(), pos.y()),
                    'zValue': item.zValue()
                }
                
                if isinstance(item, DraggableTextItem):
                    item_data['text'] = item.toPlainText()
                    item_data['font'] = item.font().toString()
                    item_data['color'] = item.defaultTextColor().name()
                
                elif isinstance(item, DraggableCircleItem):
                    rect = item.rect()
                    item_data['width'] = rect.width()
                    item_data['height'] = rect.height()
                    item_data['pen'] = {
                        'color': item.pen().color().name(),
                        'width': item.pen().width(),
                        'style': item.pen().style(),
                        'cap': item.pen().capStyle(),
                        'join': item.pen().joinStyle()
                    }
                    brush = item.brush()
                    if brush.style() == Qt.NoBrush:
                        item_data['brush_style'] = Qt.NoBrush
                    else:
                        item_data['brush_style'] = brush.style()
                        item_data['brush_color'] = brush.color().name()
                
                elif isinstance(item, DraggableRectangleItem):
                    rect = item.rect()
                    item_data['width'] = rect.width()
                    item_data['height'] = rect.height()
                    item_data['pen'] = {
                        'color': item.pen().color().name(),
                        'width': item.pen().width(),
                        'style': item.pen().style(),
                        'cap': item.pen().capStyle(),
                        'join': item.pen().joinStyle()
                    }

                    brush = item.brush()
                    if brush.style() == Qt.NoBrush:
                        item_data['brush_style'] = Qt.NoBrush
                    else:
                        item_data['brush_style'] = brush.style()
                        item_data['brush_color'] = brush.color().name()
                
                elif isinstance(item, DraggableLineItem):
                    line = item.line()
                    item_data['x1'] = line.x1()
                    item_data['y1'] = line.y1()
                    item_data['x2'] = line.x2()
                    item_data['y2'] = line.y2()
                    item_data['pen'] = {
                        'color': item.pen().color().name(),
                        'width': item.pen().width(),
                        'style': item.pen().style(),
                        'cap': item.pen().capStyle(),
                        'join': item.pen().joinStyle()
                    }
                
                items_data.append(item_data)
            
            # Currently, we are not saving the state for these item types
            # elif isinstance(item, (DraggablePathItem, DraggablePolygonItem, DraggablePixmapItem)):
                # Code to save the state of these items will go here
                # DraggablePathItem için:
                # For DraggablePathItem:
                #   item_data['path_type'] = 'simple'
                #   item_data['pen'] = { 'color': item.pen().color().name(), ... }
                # 
                # DraggablePixmapItem için:
                #   pixmap = item.pixmap()
                #   byte_array = QByteArray()
                #   buffer = QBuffer(byte_array)
                #   buffer.open(QBuffer.WriteOnly)
                #   pixmap.save(buffer, "PNG")
                #   item_data['pixmap_base64'] = str(byte_array.toBase64())
                #
                # DraggablePolygonItem için:
                #   polygon = item.polygon()
                #   points = []
                #   for i in range(polygon.count()):
                #       point = polygon.at(i)
                #       points.append((point.x(), point.y()))
                #   item_data['points'] = points
                #   item_data['pen'] = { 'color': item.pen().color().name(), ... }
                #   brush = item.brush()
                #   if brush.style() == Qt.NoBrush:
                #       item_data['brush_style'] = Qt.NoBrush
                #   else:
                #       item_data['brush_style'] = brush.style()
                #       item_data['brush_color'] = brush.color().name()
        
        # Prepare the undo state
        state = {
            'image': self.image.copy() if self.image is not None else None,
            'items': items_data
        }
        
        # Debug the current state
        self.emit_debug(f"save_state called: history length={len(self.history)}, current_index={self.current_history_index}", DebugLevel.INFO)
        self.emit_debug(f"Number of items saved: {len(items_data)}", DebugLevel.INFO)
        
        # Update the history list
        # If there were changes made that created space for redo, clear them
        if self.current_history_index < len(self.history) - 1:
            old_length = len(self.history)
            self.history = self.history[:self.current_history_index + 1]
            self.emit_debug(f"History truncated: {old_length} -> {len(self.history)}", DebugLevel.INFO)
        
        # Add the new state to the history
        self.history.append(state)
        self.current_history_index = len(self.history) - 1
        self.emit_debug(f"New state added, new index: {self.current_history_index}, history length: {len(self.history)}", DebugLevel.INFO)
        
        # Check history size
        if len(self.history) > self.max_history_size:
            self.history.pop(0)
            self.current_history_index -= 1
            self.emit_debug(f"History size limited, new index: {self.current_history_index}", DebugLevel.INFO)
        
        # Update signals
        self.undoStateChanged.emit(self.can_undo())
        self.redoStateChanged.emit(self.can_redo())
        self.emit_debug(f"Durum geçmişe kaydedildi: can_undo={self.can_undo()}, can_redo={self.can_redo()}", DebugLevel.INFO)
    
    def can_undo(self):
        """Checks if the undo operation is possible"""
        return self.current_history_index > 0
        
    def can_redo(self):
        """Checks if the redo operation is possible"""
        return self.current_history_index < len(self.history) - 1
    
    def undo(self):
        """Undoes the last operation"""
        self.emit_debug(f"undo called: index={self.current_history_index}, history length={len(self.history)}", DebugLevel.INFO)
        
        if not self.can_undo():
            self.emit_debug("Nothing to undo", DebugLevel.WARNING)
            return
        
        # Print current state for debugging
        if self.current_history_index >= 0 and self.current_history_index < len(self.history):
            current_state = self.history[self.current_history_index]
            current_image_shape = current_state['image'].shape if current_state['image'] is not None else "None"
            self.emit_debug(f"Current state: index={self.current_history_index}, image shape={current_image_shape}, items={len(current_state['items'])}", DebugLevel.INFO)
        
        # Go to the previous state
        self.current_history_index -= 1
        state = self.history[self.current_history_index]
        
        # Print target state for debugging
        target_image_shape = state['image'].shape if state['image'] is not None else "None"
        self.emit_debug(f"Target state: index={self.current_history_index}, image shape={target_image_shape}, items={len(state['items'])}", DebugLevel.INFO)
        
        # Clear draggable items from the scene
        self._clear_draggable_items()
        
        # Restore the image
        if state['image'] is not None:
            self.image = state['image'].copy()
            self.update_view()
            self.emit_debug(f"Image restored, shape={self.image.shape}", DebugLevel.INFO)
        else:
            self.emit_debug("No image to restore!", DebugLevel.ERROR)
        
        # Restore items
        self._restore_items(state['items'])
        
        self.undoStateChanged.emit(self.can_undo())
        self.redoStateChanged.emit(self.can_redo())
        self.emit_debug(f"Operation undone, new state: can_undo={self.can_undo()}, can_redo={self.can_redo()}", DebugLevel.INFO)
    
    def redo(self):
        """Redoes the last undone operation"""
        self.emit_debug(f"redo👑 called: index={self.current_history_index}, history length={len(self.history)}", DebugLevel.INFO)
        
        if not self.can_redo():
            self.emit_debug("Nothing to redo", DebugLevel.WARNING)
            return
        
        # Print current state for debugging
        if self.current_history_index >= 0 and self.current_history_index < len(self.history):
            current_state = self.history[self.current_history_index]
            current_image_shape = current_state['image'].shape if current_state['image'] is not None else "None"
            self.emit_debug(f"Current state: index={self.current_history_index}, image shape={current_image_shape}, items={len(current_state['items'])}", DebugLevel.INFO)
        
        # Go to the next state
        self.current_history_index += 1
        state = self.history[self.current_history_index]
        
        # Print target state for debugging
        target_image_shape = state['image'].shape if state['image'] is not None else "None"
        self.emit_debug(f"Hedef durum: index={self.current_history_index}, image shape={target_image_shape}, items={len(state['items'])}", DebugLevel.INFO)
        self.emit_debug(f"Target state: index={self.current_history_index}, image shape={target_image_shape}, items={len(state['items'])}", DebugLevel.INFO)
        
        # Clear draggable items from the scene
        self._clear_draggable_items()
        
        # Restore the image (forward)
        if state['image'] is not None:
            self.image = state['image'].copy()
            self.update_view()
            self.emit_debug(f"Image restored (redo), shape={self.image.shape}", DebugLevel.INFO)
        else:
            self.emit_debug("No image to restore (redo)!", DebugLevel.ERROR)
        
        # Restore items
        self._restore_items(state['items'])
        
        self.undoStateChanged.emit(self.can_undo())
        self.redoStateChanged.emit(self.can_redo())
        self.emit_debug(f"Operation redone, new state: can_undo={self.can_undo()}, can_redo={self.can_redo()}", DebugLevel.INFO)
    
    def _clear_draggable_items(self):

        """Clears all draggable items from the scene"""
        items_to_remove = []
        for item in self.scene.items():

            # For now, we only clear the item types we support
            if isinstance(item, (DraggableCircleItem, DraggableRectangleItem, DraggableTextItem, DraggableLineItem)):
                items_to_remove.append(item)
            

            # NOTE: Currently not processing DraggablePathItem, DraggablePolygonItem, DraggablePixmapItem
            # elif isinstance(item, (DraggablePathItem, DraggablePolygonItem, DraggablePixmapItem)):
            #     items_to_remove.append(item)
        
        for item in items_to_remove:
            self.scene.removeItem(item)
        

        self.emit_debug(f"{len(items_to_remove)} items cleared from scene", DebugLevel.INFO)

    def _restore_items(self, items_data):

        """Restores saved items to the scene"""
        if not items_data:

            self.emit_debug("No items to restore", DebugLevel.INFO)
            return
        
        restored_count = 0
        for item_data in items_data:
            try:
                item_type = item_data['type']
                pos_x, pos_y = item_data['pos']
                

                # Recreate item based on type
                if item_type == 'DraggableTextItem' and 'text' in item_data:
                    item = DraggableTextItem(item_data['text'])
                    if 'font' in item_data:
                        font = QFont()
                        font.fromString(item_data['font'])
                        item.setFont(font)
                    if 'color' in item_data:
                        item.setDefaultTextColor(QColor(item_data['color']))
                
                elif item_type == 'DraggableCircleItem' and 'width' in item_data and 'height' in item_data:
                    item = DraggableCircleItem(0, 0, item_data['width'], item_data['height'])
                    if 'pen' in item_data:
                        pen_data = item_data['pen']
                        pen = QPen(QColor(pen_data['color']), pen_data['width'], 
                                pen_data['style'], pen_data['cap'], pen_data['join'])
                        item.setPen(pen)
                    
                    # Restore brush style correctly
                    if 'brush_style' in item_data:
                        if item_data['brush_style'] == Qt.NoBrush:
                            item.setBrush(QBrush())
                        elif 'brush_color' in item_data:
                            brush = QBrush(QColor(item_data['brush_color']), item_data['brush_style'])
                            item.setBrush(brush)
                
                elif item_type == 'DraggableRectangleItem' and 'width' in item_data and 'height' in item_data:
                    item = DraggableRectangleItem(0, 0, item_data['width'], item_data['height'])
                    if 'pen' in item_data:
                        pen_data = item_data['pen']
                        pen = QPen(QColor(pen_data['color']), pen_data['width'], 
                                pen_data['style'], pen_data['cap'], pen_data['join'])
                        item.setPen(pen)
                    
                    # Restore brush style correctly
                    if 'brush_style' in item_data:
                        if item_data['brush_style'] == Qt.NoBrush:
                            item.setBrush(QBrush())
                        elif 'brush_color' in item_data:
                            brush = QBrush(QColor(item_data['brush_color']), item_data['brush_style'])
                            item.setBrush(brush)
                
                elif item_type == 'DraggableLineItem' and all(k in item_data for k in ['x1', 'y1', 'x2', 'y2']):
                    item = DraggableLineItem(item_data['x1'], item_data['y1'], item_data['x2'], item_data['y2'])
                    if 'pen' in item_data:
                        pen_data = item_data['pen']
                        pen = QPen(QColor(pen_data['color']), pen_data['width'], 
                                pen_data['style'], pen_data['cap'], pen_data['join'])
                        item.setPen(pen)
                
                elif item_type == 'DraggablePathItem' and 'path_type' in item_data:

                    # NOTE: Currently disabling restore for path

                    self.emit_debug(f"Path restore operation is not currently supported", DebugLevel.WARNING)
                    continue
                
                elif item_type == 'DraggablePixmapItem' and 'pixmap_base64' in item_data:
                    byte_array = QByteArray.fromBase64(item_data['pixmap_base64'].encode())
                    pixmap = QPixmap()
                    pixmap.loadFromData(byte_array, "PNG")
                    item = DraggablePixmapItem(pixmap)
                
                elif item_type == 'DraggablePolygonItem' and 'points' in item_data:
                    points_list = item_data['points']
                    polygon = QPolygonF()
                    for point_x, point_y in points_list:
                        polygon.append(QPointF(point_x, point_y))
                    item = DraggablePolygonItem(polygon)
                    if 'pen' in item_data:
                        pen_data = item_data['pen']
                        pen = QPen(QColor(pen_data['color']), pen_data['width'], 
                                pen_data['style'], pen_data['cap'], pen_data['join'])
                        item.setPen(pen)
                    
                    # Restore brush style correctly
                    if 'brush_style' in item_data:
                        if item_data['brush_style'] == Qt.NoBrush:
                            item.setBrush(QBrush())
                        elif 'brush_color' in item_data:
                            brush = QBrush(QColor(item_data['brush_color']), item_data['brush_style'])
                            item.setBrush(brush)
                
                # We are currently adding basic support for DraggablePathItem
                # Full vector data support might be more complex
                elif item_type == 'DraggablePathItem' and 'path_type' in item_data:
                    # For simple paths for now
                    # if item_data['path_type'] == 'simple':
                    #     path = QPainterPath()
                    #     path.moveTo(0, 0)
                    #     path.lineTo(50, 50)  # A simple line for now
                    #     item = DraggablePathItem(path)
                    #     if 'pen' in item_data:
                    #         pen_data = item_data['pen']
                    #         pen = QPen(QColor(pen_data['color']), pen_data['width'], 
                    #                 pen_data['style'], pen_data['cap'], pen_data['join'])
                    #         item.setPen(pen)

                    self.emit_debug(f"Path restore operation is not currently supported", DebugLevel.WARNING)
                else:

                    self.emit_debug(f"Unsupported item type or missing data: {item_type}", DebugLevel.WARNING)
                    continue
                
                # Öğeyi sahneye ekle
                item.setPos(pos_x, pos_y)
                if 'zValue' in item_data:
                    item.setZValue(item_data['zValue'])
                self.scene.addItem(item)
                restored_count += 1
                
            except Exception as e:

                self.emit_debug(f"Error restoring item: {str(e)}", DebugLevel.ERROR)
                self.emit_debug(traceback.format_exc(), DebugLevel.ERROR)
        

        self.emit_debug(f"{restored_count} items restored successfully", DebugLevel.INFO)
    
    # endregion
