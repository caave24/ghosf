import sys
import threading
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.processor import GhosfProcessor, Settings


class WorkerEvents(QObject):
    progress = Signal(float, str)
    done = Signal(str)
    error = Signal(str)


class DropArea(QFrame):
    fileDropped = Signal(str)
    clicked = Signal()

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setMinimumHeight(150)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("dropArea")

        layout = QVBoxLayout(self)
        label = QLabel("DROP MEDIA HERE\n\nor click to choose a video")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            self.fileDropped.emit(urls[0].toLocalFile())
            event.acceptProposedAction()


class SliderRow(QWidget):
    def __init__(self, title, minimum, maximum, value):
        super().__init__()

        self.label = QLabel(title)
        self.label.setMinimumWidth(150)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(minimum, maximum)
        self.slider.setValue(value)

        self.spin = QSpinBox()
        self.spin.setRange(minimum, maximum)
        self.spin.setValue(value)
        self.spin.setMaximumWidth(85)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.spin)

        self.slider.valueChanged.connect(self.spin.setValue)
        self.spin.valueChanged.connect(self.slider.setValue)

    def value(self):
        return self.spin.value()


class GhosfWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.media_path = None
        self.worker = None
        self.events = WorkerEvents()

        self.setWindowTitle("ghosf")
        self.resize(780, 780)
        self.setMinimumSize(650, 650)

        self._build_ui()
        self._connect_events()

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)

        layout = QVBoxLayout(root)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(12)

        title = QLabel("ghosf")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel("sharp present + pixelated past + temporal layers")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignCenter)

        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.drop_area = DropArea()
        self.drop_area.fileDropped.connect(self.set_media)
        self.drop_area.clicked.connect(self.choose_media)
        layout.addWidget(self.drop_area)

        self.file_label = QLabel("No media selected.")
        self.file_label.setWordWrap(True)
        layout.addWidget(self.file_label)

        temporal = QGroupBox("Temporal Layers")
        temporal_layout = QVBoxLayout(temporal)

        self.interval = SliderRow("Frame interval", 1, 300, 80)
        self.history = SliderRow("Ghost history", 1, 30, 10)
        self.pixel_size = SliderRow("Oldest pixel size", 1, 64, 16)

        temporal_layout.addWidget(self.interval)
        temporal_layout.addWidget(self.history)
        temporal_layout.addWidget(self.pixel_size)

        combo_grid = QGridLayout()

        combo_grid.addWidget(QLabel("Pixel decay curve"), 0, 0)
        self.pixel_curve = QComboBox()
        self.pixel_curve.addItems(["Memory", "Linear", "Exponential"])
        combo_grid.addWidget(self.pixel_curve, 0, 1)

        combo_grid.addWidget(QLabel("Blend mode"), 1, 0)
        self.blend = QComboBox()
        self.blend.addItems(["Screen", "Normal", "Additive"])
        combo_grid.addWidget(self.blend, 1, 1)

        temporal_layout.addLayout(combo_grid)
        layout.addWidget(temporal)

        fade = QGroupBox("End Fade")
        fade_layout = QVBoxLayout(fade)

        self.end_fade_enabled = QCheckBox("Fade ghost layers before the end")
        self.end_fade_enabled.setChecked(True)
        fade_layout.addWidget(self.end_fade_enabled)

        fade_grid = QGridLayout()
        fade_grid.addWidget(QLabel("Fade frames"), 0, 0)

        self.fade_frames = QSpinBox()
        self.fade_frames.setRange(1, 300)
        self.fade_frames.setValue(20)
        fade_grid.addWidget(self.fade_frames, 0, 1)

        fade_grid.addWidget(QLabel("Cubic Bézier"), 1, 0)
        self.bezier = QLineEdit(".17,.67,.77,.42")
        fade_grid.addWidget(self.bezier, 1, 1)

        fade_layout.addLayout(fade_grid)
        layout.addWidget(fade)

        output = QGroupBox("Output")
        output_layout = QHBoxLayout(output)

        self.output_dir = QLineEdit(str(Path.cwd() / "output"))
        choose_output = QPushButton("Choose…")
        choose_output.clicked.connect(self.choose_output)

        output_layout.addWidget(self.output_dir, 1)
        output_layout.addWidget(choose_output)

        layout.addWidget(output)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.status = QLabel("Drop a video to begin.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        self.process_button = QPushButton("PROCESS MEDIA")
        self.process_button.setMinimumHeight(44)
        self.process_button.clicked.connect(self.start_processing)
        layout.addWidget(self.process_button)

        self.setStyleSheet("""
            QWidget { font-size: 13px; }
            QLabel#title { font-size: 32px; font-weight: 700; }
            QLabel#subtitle { color: #777; margin-bottom: 8px; }
            QFrame#dropArea {
                border: 2px dashed #777;
                border-radius: 10px;
                background: rgba(127,127,127,0.05);
            }
            QFrame#dropArea:hover {
                border-color: #aaa;
                background: rgba(127,127,127,0.1);
            }
            QGroupBox {
                font-weight: 600;
                margin-top: 10px;
                padding-top: 8px;
            }
        """)

    def _connect_events(self):
        self.events.progress.connect(self.on_progress)
        self.events.done.connect(self.on_done)
        self.events.error.connect(self.on_error)

    def choose_media(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose media",
            "",
            "Video files (*.mp4 *.mov *.mkv *.webm *.avi *.m4v);;All files (*.*)",
        )
        if path:
            self.set_media(path)

    def set_media(self, path):
        path = Path(path).expanduser().resolve()

        if not path.exists():
            QMessageBox.critical(self, "ghosf", "That file does not exist.")
            return

        self.media_path = path
        self.file_label.setText(str(path))
        self.status.setText("Media selected. Ready to process.")
        self.progress.setValue(0)

    def choose_output(self):
        path = QFileDialog.getExistingDirectory(self, "Choose output folder")
        if path:
            self.output_dir.setText(path)

    def start_processing(self):
        if not self.media_path:
            QMessageBox.warning(self, "ghosf", "Drop or choose a media file first.")
            return

        try:
            bezier = tuple(float(value.strip()) for value in self.bezier.text().split(","))
            if len(bezier) != 4:
                raise ValueError
        except ValueError:
            QMessageBox.warning(
                self,
                "ghosf",
                "Cubic Bézier must contain four numbers, e.g. .17,.67,.77,.42",
            )
            return

        settings = Settings(
            frame_interval=self.interval.value(),
            ghost_history=self.history.value(),
            max_pixel_size=self.pixel_size.value(),
            pixel_curve=self.pixel_curve.currentText().lower(),
            blend_mode=self.blend.currentText().lower(),
            end_fade_enabled=self.end_fade_enabled.isChecked(),
            end_fade_frames=self.fade_frames.value(),
            fade_bezier=bezier,
        )

        self.process_button.setEnabled(False)
        self.progress.setValue(0)
        self.status.setText("Starting ghosf…")

        processor = GhosfProcessor(
            self.media_path,
            Path(self.output_dir.text()).expanduser(),
            settings,
            self.emit_event,
        )

        self.worker = threading.Thread(
            target=self.run_processor,
            args=(processor,),
            daemon=True,
        )
        self.worker.start()

    def run_processor(self, processor):
        try:
            output = processor.run()
            self.events.done.emit(str(output))
        except Exception as exc:
            self.events.error.emit(str(exc))

    def emit_event(self, event):
        kind = event[0]
        if kind == "progress":
            _, percent, message = event
            self.events.progress.emit(percent, message)

    def on_progress(self, percent, message):
        self.progress.setValue(round(percent))
        self.status.setText(message)

    def on_done(self, output):
        self.progress.setValue(100)
        self.status.setText(f"Done: {output}")
        self.process_button.setEnabled(True)
        QMessageBox.information(self, "ghosf", f"ghosf complete.\n\n{output}")

    def on_error(self, message):
        self.status.setText("Processing failed.")
        self.process_button.setEnabled(True)
        QMessageBox.critical(self, "ghosf", message)


def main():
    app = QApplication(sys.argv)
    window = GhosfWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
