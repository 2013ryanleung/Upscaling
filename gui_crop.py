
import os
import sys
from PyQt5 import QtGui
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtMultimedia import *
from PyQt5.QtMultimediaWidgets import *

import cv2
from cv2 import dnn_superres
from img_ops import upscale_ff
from PIL import Image


class MQLabel(QLabel):
    
    mousePressed = pyqtSignal(QMouseEvent)
    mouseMoved = pyqtSignal(QMouseEvent)
    mouseReleased = pyqtSignal(QMouseEvent)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_Hover)
    
    def mousePressEvent(self, event):
        self.mousePressed.emit(event)
        event.accept()

    def mouseMoveEvent(self, event):
        self.mouseMoved.emit(event)
        event.accept()

    def mouseReleaseEvent(self, event):
        self.mouseReleased.emit(event)
        event.accept()


class ImageWidget(QWidget):

    def __init__(self, image_path):
        super().__init__()
        self.setMouseTracking(True)

        # Initialise variables
        self.drag_start = None
        self.edge_status = {'left': False, 
                            'right': False, 
                            'top': False, 
                            'bottom': False,
                            'top_left': False,
                            'top_right': False,
                            'bottom_left': False,
                            'bottom_right': False}
        self.mode = None
        self.unlock = True
        self.resizeEdge = None
        
        # Load the image
        self.image = QPixmap(image_path)

        # Create a QLabel to display the image
        self.label = MQLabel(self)
        self.label.setScaledContents(True)
        self.label.mousePressed.connect(self.mousePressEvent)
        self.label.mouseMoved.connect(self.mouseMoveEvent)
        self.label.mouseReleased.connect(self.mouseReleaseEvent)
        self.label.setPixmap(self.image)

        # Create a QRect to draw the rectangle
        self.rect = QRect(0, 0, 100, 100)
        self.rect_pen = QPen(QColor(255, 0, 0), 1)
        self.rect_brush = QBrush(Qt.NoBrush)

        # Set the size of the widget to the size of the image
        self.setFixedSize(self.image.width(), self.image.height())

    def paintEvent(self, event):
        # Call the paintEvent of the parent class
        super().paintEvent(event)

        # Clear the pixmap of the QLabel
        self.label.setPixmap(self.image)

        # Create a QPainter to draw the rectangle on the QLabel
        painter = QPainter(self.label.pixmap())
        painter.setPen(self.rect_pen)
        painter.setBrush(self.rect_brush)
        painter.drawRect(self.rect)
        painter.end()

    # Lock mode to prevent changing the mode while the mouse is pressed due to mouse moving too fast
    def mousePressEvent(self, event):

        print(f'Pressed')

        if self.unlock:
            self.unlock = False
            self.lockedMode = self.mode
            self.lockedEdge = self.resizeEdge

        if self.lockedMode == 'move':
            self.drag_start = event.pos() - self.rect.topLeft()

        elif self.lockedMode == 'resize':
            if self.lockedEdge == 'top_left':
                self.drag_start = event.pos() - self.rect.topLeft()
            elif self.lockedEdge == 'top_right':
                self.drag_start = event.pos() - self.rect.topRight()
            elif self.lockedEdge == 'bottom_left':
                self.drag_start = event.pos() - self.rect.bottomLeft()
            elif self.lockedEdge == 'bottom_right':
                self.drag_start = event.pos() - self.rect.bottomRight()
            elif self.lockedEdge == 'top':
                self.drag_start = event.pos() - self.rect.topLeft()
            elif self.lockedEdge == 'right':
                self.drag_start = event.pos() - self.rect.bottomRight()
            elif self.lockedEdge == 'bottom':
                self.drag_start = event.pos() - self.rect.bottomLeft()
            elif self.lockedEdge == 'left':
                self.drag_start = event.pos() - self.rect.topLeft()
            
    def mouseMoveEvent(self, event):

        #print(f'Position: {event.pos()}')

        EDGE_THRESH = 10

        # Check if the mouse is near any of the edges or corners of the rectangle
        self.edge_status['left'] = self.rect.left() - EDGE_THRESH < event.pos().x() < self.rect.left() + EDGE_THRESH and \
                                    self.rect.top() - EDGE_THRESH < event.pos().y() < self.rect.bottom() + EDGE_THRESH
        self.edge_status['right'] = self.rect.right() - EDGE_THRESH < event.pos().x() < self.rect.right() + EDGE_THRESH and \
                                    self.rect.top() - EDGE_THRESH < event.pos().y() < self.rect.bottom() + EDGE_THRESH
        self.edge_status['top'] = self.rect.top() - EDGE_THRESH < event.pos().y() < self.rect.top() + EDGE_THRESH and \
                                self.rect.left() - EDGE_THRESH < event.pos().x() < self.rect.right() + EDGE_THRESH
        self.edge_status['bottom'] = self.rect.bottom() - EDGE_THRESH < event.pos().y() < self.rect.bottom() + EDGE_THRESH and \
                                    self.rect.left() - EDGE_THRESH < event.pos().x() < self.rect.right() + EDGE_THRESH
        self.edge_status['top_left'] = self.edge_status['left'] and self.edge_status['top']
        self.edge_status['top_right'] = self.edge_status['right'] and self.edge_status['top']
        self.edge_status['bottom_left'] = self.edge_status['left'] and self.edge_status['bottom']
        self.edge_status['bottom_right'] = self.edge_status['right'] and self.edge_status['bottom']

        # Check if mouse is inside the rectangle and not near any of the edges or corners
        if not any(self.edge_status.values()) and not self.rect.contains(event.pos()):
            self.setCursor(Qt.ArrowCursor)
            self.mode = None

        elif any(self.edge_status.values()):
            self.mode = 'resize'

            # Change the cursor shape if the mouse is near any of the edges or corners of the rectangle
            if self.edge_status['top_left'] or self.edge_status['bottom_right']:
                self.setCursor(Qt.SizeFDiagCursor)
                self.resizeEdge = 'top_left' if self.edge_status['top_left'] else 'bottom_right'
            elif self.edge_status['top_right'] or self.edge_status['bottom_left']:
                self.setCursor(Qt.SizeBDiagCursor)
                self.resizeEdge = 'top_right' if self.edge_status['top_right'] else 'bottom_left'
            elif self.edge_status['left'] or self.edge_status['right']:
                self.setCursor(Qt.SizeHorCursor)
                self.resizeEdge = 'left' if self.edge_status['left'] else 'right'
            elif self.edge_status['top'] or self.edge_status['bottom']:
                self.setCursor(Qt.SizeVerCursor)
                self.resizeEdge = 'top' if self.edge_status['top'] else 'bottom'

        elif self.rect.contains(event.pos()):
            self.mode = 'move'
            self.setCursor(Qt.SizeAllCursor)

        else:
            raise Exception('Something went wrong')

        if self.drag_start is not None: # Also means mouse is pressed, locked defined

            new_pos = event.pos() - self.drag_start

            if self.lockedMode == 'move':
                self.rect.moveTopLeft(new_pos)
            elif self.lockedMode == 'resize':
                if self.lockedEdge == 'top' or self.lockedEdge == 'top_left' or self.lockedEdge == 'top_right':
                    newSize = self.rect.bottomLeft() - new_pos
                    if not newSize.y() < 2*EDGE_THRESH:
                        self.rect.setTop(new_pos.y())
                if self.lockedEdge == 'right' or self.lockedEdge == 'top_right' or self.lockedEdge == 'bottom_right':
                    newSize = self.rect.topLeft() - new_pos
                    if not -newSize.x() < 2*EDGE_THRESH:
                        self.rect.setRight(new_pos.x())
                if self.lockedEdge == 'bottom' or self.lockedEdge == 'bottom_left' or self.lockedEdge == 'bottom_right':
                    newSize = self.rect.topLeft() - new_pos
                    if not -newSize.y() < 2*EDGE_THRESH:
                        self.rect.setBottom(new_pos.y())
                if self.lockedEdge == 'left' or self.lockedEdge == 'top_left' or self.lockedEdge == 'bottom_left':
                    newSize = self.rect.topRight() - new_pos
                    if not newSize.x() < 2*EDGE_THRESH:
                        self.rect.setLeft(new_pos.x())

            self.update()

    def mouseReleaseEvent(self, event):
        self.drag_start = None
        self.unlock = True
        print('Released')


class MainWindow(QWidget):
    
    def __init__(self):
        super(MainWindow, self).__init__()
        self.initUI()

    def initUI(self):
        
        # Create the ImageWidget
        self.image_widget = ImageWidget("medias/New_0 degree - Plan view_x0.5.png")

        box = QVBoxLayout(self)
        box.addWidget(self.image_widget)
        self.setLayout(box)

        self.setMouseTracking(True)

        QApplication.setStyle(QStyleFactory.create('Fusion'))
        self.setWindowTitle("GUI")
        self.show()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.NoButton:
            # print coordinates
            print(event.pos())


app = QCoreApplication.instance()
if app is None:
    app = QApplication([])
window = MainWindow()
window.show()

try:
    from IPython.lib.guisupport import start_event_loop_qt5
    start_event_loop_qt5(app)
except ImportError:
    app.exec_()