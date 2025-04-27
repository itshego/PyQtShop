# draggable_items.py

from PyQt5.QtWidgets import (QGraphicsTextItem, QGraphicsEllipseItem, QGraphicsRectItem,
                             QGraphicsItem, QGraphicsLineItem,
                             QGraphicsPathItem, QGraphicsPixmapItem, QGraphicsPolygonItem)
from PyQt5.QtCore import Qt, pyqtSignal, QObject


class SignalEmitter(QObject):
    cursorChanged = pyqtSignal(Qt.CursorShape)


class DraggableItemMixin:
    def init_draggable(self):
        self.setFlag(QGraphicsItem.ItemIsMovable, False)
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.setAcceptHoverEvents(True)
        self.signal_emitter = SignalEmitter()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.isSelected():
            self.signal_emitter.cursorChanged.emit(Qt.ClosedHandCursor)
        QGraphicsItem.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.isSelected():
            self.signal_emitter.cursorChanged.emit(Qt.OpenHandCursor)
        QGraphicsItem.mouseReleaseEvent(self, event)

    def hoverEnterEvent(self, event):
        self.signal_emitter.cursorChanged.emit(Qt.PointingHandCursor)
        QGraphicsItem.hoverEnterEvent(self, event)

    def hoverLeaveEvent(self, event):
        self.signal_emitter.cursorChanged.emit(Qt.ArrowCursor)
        QGraphicsItem.hoverLeaveEvent(self, event)

    def enable_dragging(self):
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def disable_dragging(self):
        self.setFlag(QGraphicsItem.ItemIsMovable, False)
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)


class DraggableTextItem(QGraphicsTextItem, DraggableItemMixin):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.init_draggable()
        self.setTextInteractionFlags(Qt.TextEditorInteraction)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if self.textInteractionFlags() & Qt.TextEditorInteraction:
            self.signal_emitter.cursorChanged.emit(Qt.IBeamCursor)
        else:
            self.signal_emitter.cursorChanged.emit(Qt.ClosedHandCursor)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if self.textInteractionFlags() & Qt.TextEditorInteraction:
            self.signal_emitter.cursorChanged.emit(Qt.IBeamCursor)
        else:
            self.signal_emitter.cursorChanged.emit(Qt.OpenHandCursor)


class DraggableCircleItem(QGraphicsEllipseItem, DraggableItemMixin):
    def __init__(self, x, y, width, height, parent=None):
        super().__init__(x, y, width, height, parent)
        self.init_draggable()


class DraggableRectangleItem(QGraphicsRectItem, DraggableItemMixin):
    def __init__(self, x, y, width, height, parent=None):
        super().__init__(x, y, width, height, parent)
        self.init_draggable()


class DraggableLineItem(QGraphicsLineItem, DraggableItemMixin):
    def __init__(self, x1, y1, x2, y2, parent=None):
        super().__init__(x1, y1, x2, y2, parent)
        self.init_draggable()


class DraggablePathItem(QGraphicsPathItem, DraggableItemMixin):
    def __init__(self, path, parent=None):
        super().__init__(path, parent)
        self.init_draggable()


class DraggablePixmapItem(QGraphicsPixmapItem, DraggableItemMixin):
    def __init__(self, pixmap, parent=None):
        super().__init__(pixmap, parent)
        self.init_draggable()


class DraggablePolygonItem(QGraphicsPolygonItem, DraggableItemMixin):
    def __init__(self, polygon, parent=None):
        super().__init__(polygon, parent)
        self.init_draggable()
