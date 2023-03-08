import os
import sys
import PIL
import PIL.Image
import PIL.ImageQt
from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtWidgets import QToolBar, QAction, QFileDialog, QInputDialog, QListWidgetItem, QMessageBox
from image_scaling import Resizer


class ImageAnnotator(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self._target_height, self._target_width = 1920, 1080
        self._is_saved = True

    def initUI(self):
        # Create a QLabel to display the image
        self._image_label = QtWidgets.QLabel(self)
        self._image_label.setAlignment(Qt.AlignCenter)
        self.setCentralWidget(self._image_label)
        self._m_pixmap = QPixmap()
        self._image_label.setPixmap(self._m_pixmap)

        # Create a QDockWidget to hold the keypoints list
        self._keypoints_dock = QtWidgets.QDockWidget(self)
        self._keypoints_dock.setFixedWidth(150)
        self.addDockWidget(Qt.RightDockWidgetArea, self._keypoints_dock)

        # Create a QListWidget to display the key points
        self._keypoints_list = QtWidgets.QListWidget()
        self._keypoints_list.itemChanged.connect(self.update)
        self._keypoints_dock.setWidget(self._keypoints_list)

        # Create the left toolbar
        self.create_left_toolbar()

        # Connect the mousePressEvent to the add_keypoint function
        self._image_label.mousePressEvent = self.add_keypoint

        # Connect the paintEvent to the draw key points function
        self._image_label.paintEvent = self.draw_keypoints

        self.show()

    def create_left_toolbar(self):
        self._left_toolbar = QToolBar("Left Toolbar")
        self._left_toolbar.setIconSize(QSize(32, 32))
        self._left_toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.addToolBar(Qt.LeftToolBarArea, self._left_toolbar)

        # Create the "Open dir" action
        self._openDirAction = QAction(QIcon(os.path.join("resources", "icons", "open.png")), "Open dir", self)
        self._openDirAction.triggered.connect(self.open_dir)
        self._left_toolbar.addAction(self._openDirAction)

        # Create the "Next image" action
        self._nextImageAction = QAction(QIcon(os.path.join("resources", "icons", "next.png")), "Next image", self)
        self._nextImageAction.triggered.connect(self.next_image)
        self._left_toolbar.addAction(self._nextImageAction)

        # Create the "Prev image" action
        self._prevImageAction = QAction(QIcon(os.path.join("resources", "icons", "prev.png")), "Prev image", self)
        self._prevImageAction.triggered.connect(self.prev_image)
        self._left_toolbar.addAction(self._prevImageAction)

        # Create the "Save" action
        self._saveAction = QAction(QIcon(os.path.join("resources", "icons", "save.png")), "Save", self)
        self._saveAction.triggered.connect(self.save)
        self._left_toolbar.addAction(self._saveAction)

    def open_dir(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        directory = QFileDialog.getExistingDirectory(self, "Select a directory", options=options)
        if directory:
            with open(os.path.join(directory, "classes.txt"), "r") as file:
                self._class_names = file.readlines()
            self._current_directory = directory
            self._image_filenames = [
                name for name in os.listdir(directory)
                if any(name.endswith(ext) for ext in ['.jpg', '.png', '.gif', '.jpeg'])
            ]
            self._current_image_index = 0
            self.load_image()

    def next_image(self):
        if self._current_image_index == len(self._image_filenames) - 1:
            return
        if not self._is_saved:
            if self._ask_for_saving() == QMessageBox.Yes:
                self.save()
            self._is_saved = True
        self._keypoints_list.clear()
        self._current_image_index += 1
        self.load_image()

    def prev_image(self):
        if self._current_image_index == 0:
            return
        if not self._is_saved:
            if self._ask_for_saving() == QMessageBox.Yes:
                self.save()
            self._is_saved = True
        self._keypoints_list.clear()
        self._current_image_index -= 1
        self.load_image()

    def save(self):
        filename, _ = QFileDialog.getSaveFileName(self, 'Save File', '', 'Text Files (*.txt)')
        if filename:
            with open(filename, 'w') as file:
                for i in range(self._keypoints_list.count()):
                    file.write(self._keypoints_list.item(i).text() + "\n")
        self._is_saved = True
        self.update()

    def add_keypoint(self, event):
        x, y = event.pos().x(), event.pos().y()
        class_name, ok = QInputDialog.getItem(self, "Select class dialog",
                                              "List of classes", self._class_names, 0, False)
        item = QListWidgetItem(f"{self._class_names.index(class_name)}, {x}, {y}")
        item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)
        self._keypoints_list.addItem(item)
        self._is_saved = False
        self.update()

    def draw_keypoints(self, event):
        super().paintEvent(event)
        painter = QtGui.QPainter(self._image_label)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setPen(QtGui.QPen(Qt.red, 10))
        painter.drawPixmap(event.rect(), self._m_pixmap)
        for i in range(self._keypoints_list.count()):
            point_str = self._keypoints_list.item(i).text()
            x, y = [int(coord.strip("()")) for coord in point_str.split(",")[1:]]
            painter.drawPoint(x, y)
        painter.end()

    def load_image(self):
        image_path = os.path.join(self._current_directory, self._image_filenames[self._current_image_index])
        image = PIL.Image.open(image_path)
        resizer = Resizer(self._target_height, self._target_width)
        image = resizer.resize_with_pad(image)
        self._m_pixmap = PIL.ImageQt.toqpixmap(image)
        self._image_label.setPixmap(self._m_pixmap)
        self.setGeometry(QtCore.QRect(0, 30, self._m_pixmap.width() + 150, self._m_pixmap.height()))
        txt_file = os.path.join(self._current_directory,
                                self._image_filenames[self._current_image_index].split(".")[0] + ".txt")
        if os.path.exists(txt_file):
            with open(txt_file, "r") as file:
                for line in file:
                    item = QListWidgetItem(f"{line.strip()}")
                    item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)
                    self._keypoints_list.addItem(item)

    def _ask_for_saving(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Question)
        msg.setText("Do you want to save the points?")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        retval = msg.exec_()
        return retval


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = ImageAnnotator()
    sys.exit(app.exec_())
