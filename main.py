import os
import sys
import subprocess
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QLineEdit, QPushButton, QTextEdit, QFileDialog,
                               QMessageBox, QSpacerItem, QSizePolicy)
from PySide6.QtGui import QPixmap, QTextCursor, QIcon, QMouseEvent
from PySide6.QtCore import Qt, QThread, Signal, QObject, QPoint

base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
cli_folder = os.path.join(base_dir, 'CLI')
cli_path = os.path.join(cli_folder, '.exe')

def get_resource_path(other_path):
    try:
        temp_dir = sys._MEIPASS
    except AttributeError:
        temp_dir = os.path.abspath(".")
    return os.path.join(temp_dir, other_path)

creation_flags = {}
if sys.platform == 'win32':
    creation_flags['creationflags'] = subprocess.CREATE_NO_WINDOW

class CustomTitleBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_window = parent
        self.setAutoFillBackground(True)
        self.setObjectName("titleBar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(0)

        self.title_label = QLabel("Steamless Auto")
        self.title_label.setObjectName("titleLabel")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.min_button = QPushButton("–")
        self.min_button.setObjectName("minButton")
        self.min_button.clicked.connect(self.parent_window.showMinimized)

        self.close_button = QPushButton("✕")
        self.close_button.setObjectName("closeButton")
        self.close_button.clicked.connect(self.parent_window.close)

        layout.addWidget(self.title_label, stretch=1)
        layout.addWidget(self.min_button)
        layout.addWidget(self.close_button)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.parent_window.old_pos = event.globalPosition().toPoint()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.parent_window.old_pos:
            delta = QPoint(event.globalPosition().toPoint() - self.parent_window.old_pos)
            self.parent_window.move(self.parent_window.x() + delta.x(), self.parent_window.y() + delta.y())
            self.parent_window.old_pos = event.globalPosition().toPoint()
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.parent_window.old_pos = None
        event.accept()

class Worker(QObject):
    log_signal = Signal(str)
    finished = Signal()

    def __init__(self, folder_path, cli_path):
        super().__init__()
        self.folder_path = folder_path
        self.cli_path = cli_path

    def run(self):
        if not os.path.exists(self.cli_path):
            self.log_signal.emit(f"Error: Steamless CLI not found at '{self.cli_path}'. Aborting.\n")
            self.finished.emit()
            return
        if not os.path.isdir(self.folder_path):
            self.log_signal.emit(f"Error: Invalid folder path '{self.folder_path}'. Aborting.\n")
            self.finished.emit()
            return
        self.log_signal.emit(f"Starting to process folder: {self.folder_path}\n")
        found_exe = False
        processed_count = 0
        failed_count = 0
        for root, _, files in os.walk(self.folder_path):
            for file in files:
                if file.lower().endswith('.exe'):
                    found_exe = True
                    file_path = os.path.join(root, file)
                    self.log_signal.emit(f"Processing: {os.path.basename(file_path)}...")
                    try:
                        process = subprocess.Popen([self.cli_path, file_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **creation_flags)
                        process.wait(timeout=300)
                        if process.returncode == 0:
                            self.log_signal.emit(f" Successfully processed: {os.path.basename(file_path)}\n")
                            processed_count +=1
                        else:
                            self.log_signal.emit(f" Failed to process: {os.path.basename(file_path)} (Error Code: {process.returncode})\n")
                            failed_count += 1
                    except subprocess.TimeoutExpired:
                        self.log_signal.emit(f" Timeout processing: {os.path.basename(file_path)}\n")
                        if process: process.kill()
                        failed_count += 1
                    except Exception as e:
                        self.log_signal.emit(f" Error during processing of {os.path.basename(file_path)}: {e}\n")
                        failed_count += 1
                        
            self.log_signal.emit(f"Processing summary: {processed_count} succeeded, {failed_count} failed.\n")
        self.log_signal.emit("Processing finished.\n")
        self.finished.emit()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setFixedSize(420, 320)

        self.thread = None
        self.worker = None
        self.old_pos = None

        self.setStyleSheet("""
            QMainWindow { background-color: #3a3a3a; }
            QWidget { color: #cccccc; font-family: Arial, sans-serif; }
            QWidget#titleBar { background-color: #3a3a3a; }
            QLabel#titleLabel { font-weight: bold; font-size: 13px; }
            QPushButton#menuButton, QPushButton#minButton, QPushButton#closeButton {
                background-color: transparent; border: none; font-size: 16px; padding: 5px 10px;
            }
            QPushButton#minButton:hover, QPushButton#menuButton:hover { background-color: #505050; }
            QPushButton#closeButton:hover { background-color: #ff0000; }
            QLabel#folderLabel { font-size: 14px; }
            QLineEdit, QTextEdit {
                background-color: #505050; border: none; border-radius: 5px; padding: 8px; font-size: 12px;
            }
            QPushButton#browseButton, QPushButton#processButton {
                background-color: #505050; border: none; border-radius: 5px; padding: 10px;
                font-size: 14px; font-weight: bold;
            }
            QPushButton#browseButton:hover, QPushButton#processButton:hover { background-color: #616161; }
            QPushButton:disabled { background-color: #404040; color: #888888; }
            QLabel#footerLabel { color: #a0a0c0; font-size: 11px; font-style: italic; }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.title_bar = CustomTitleBar(self)
        main_layout.addWidget(self.title_bar)
        
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(15, 10, 15, 15)
        layout.setSpacing(12)

        logo_gui_path = get_resource_path('icon_steamless/logosteamless.png')
        self.logo_label = QLabel()
        if os.path.exists(logo_gui_path):
            pixmap = QPixmap(logo_gui_path)
            self.logo_label.setPixmap(pixmap.scaledToWidth(400, Qt.TransformationMode.SmoothTransformation))
        else:
            self.logo_label.setText("STEAMLESS AUTO")
            self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.logo_label.setStyleSheet("font-size: 40px; font-weight: bold; padding: 40px 0;")
        layout.addWidget(self.logo_label, alignment=Qt.AlignmentFlag.AlignCenter)

        window_icon_gui_path = get_resource_path('icon_steamless/steamless.ico')
        if os.path.exists(window_icon_gui_path):
            self.setWindowIcon(QIcon(window_icon_gui_path))

        folder_layout = QHBoxLayout()
        folder_label = QLabel('Select Folder:')
        folder_label.setObjectName("folderLabel")
        self.folder_entry = QLineEdit()
        self.folder_entry.setText(self.get_default_directory())
        self.browse_button = QPushButton('Browse')
        self.browse_button.setObjectName("browseButton")
        self.browse_button.clicked.connect(self.select_folder)
        folder_layout.addWidget(folder_label)
        folder_layout.addWidget(self.folder_entry, stretch=1)
        folder_layout.addWidget(self.browse_button)
        folder_layout.setSpacing(10)
        layout.addLayout(folder_layout)
        
        self.process_button = QPushButton('Remove Steam DRM')
        self.process_button.setObjectName("processButton")
        self.process_button.clicked.connect(self.start_processing)
        layout.addWidget(self.process_button)

        self.log_widget = QTextEdit()
        self.log_widget.setReadOnly(True)
        layout.addWidget(self.log_widget, stretch=1)
        
        self.footer_label = QLabel("Made by Helstorm [Mike]")
        self.footer_label.setObjectName("footerLabel")
        self.footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.footer_label)
        
        main_layout.addWidget(content_widget, stretch=1)

    def get_default_directory(self):
        default_dir = 'C:\\Program Files (x86)\\Steam\\steamapps\\common'
        return default_dir if os.path.exists(default_dir) else os.path.expanduser("~")

    def select_folder(self):
        start_dir = self.folder_entry.text()
        if not os.path.isdir(start_dir):
            start_dir = self.get_default_directory()
        folder_path = QFileDialog.getExistingDirectory(self, 'Select Folder', start_dir)
        if folder_path:
            self.folder_entry.setText(folder_path)

    def start_processing(self):
        folder_path = self.folder_entry.text().strip()
        if not os.path.exists(cli_path):
            QMessageBox.critical(self, "Error", f".exe is not found at the expected location:\n{cli_path}\nPlease ensure it's correctly bundled.")
            return
        if not folder_path or not os.path.isdir(folder_path):
            QMessageBox.warning(self, "Invalid Folder", "The selected folder path is not valid. Please select a valid folder.")
            return
        normalized_folder_path = os.path.normpath(folder_path).lower()
        common_steam_path = os.path.normpath('C:\\Program Files (x86)\\Steam\\steamapps\\common').lower()
        common_steam_path_64 = os.path.normpath('C:\\Program Files\\Steam\\steamapps\\common').lower()
        if normalized_folder_path == common_steam_path or normalized_folder_path == common_steam_path_64:
            response = QMessageBox.question(self, 'Warning', "You are about to scan a main Steam 'common' folder. This could take a very long time and affect many files.\n\nDo you wish to proceed?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if response == QMessageBox.StandardButton.No:
                self.log_widget.append('Operation canceled by user (common folder scan).\n')
                return
        if self.thread and self.thread.isRunning():
            QMessageBox.information(self, "In Progress", "Processing is already in progress. Please wait.")
            return

        self.process_button.setEnabled(False)
        self.browse_button.setEnabled(False)
        self.log_widget.clear()
        self.log_widget.append(f"Initializing processing for: {folder_path}\n")
        self.thread = QThread()
        self.worker = Worker(folder_path, cli_path)
        self.worker.moveToThread(self.thread)
        self.worker.log_signal.connect(self.update_log)
        self.worker.finished.connect(self._on_processing_finished)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.started.connect(self.worker.run)
        self.thread.start()

    def _on_processing_finished(self):
        self.process_button.setEnabled(True)
        self.browse_button.setEnabled(True)
        self.log_widget.append("------------------------------\n")
        QMessageBox.information(self, "Complete", "Processing has finished.")
        self.thread = None
        self.worker = None

    def update_log(self, message):
        self.log_widget.moveCursor(QTextCursor.MoveOperation.End)
        self.log_widget.insertPlainText(message)
        self.log_widget.ensureCursorVisible()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
