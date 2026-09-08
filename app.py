import sys
import threading
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFrame, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPushButton, QProgressBar, QSlider, QSpinBox, QVBoxLayout, QWidget,
)

from core.config_code import decode_settings, encode_settings, short_fingerprint
from core.processor import GhosfProcessor, ProcessingCancelled, Settings


class WorkerEvents(QObject):
    progress = Signal(float, str)
    done = Signal(str)
    cancelled = Signal()
    error = Signal(str)


class DropArea(QFrame):
    fileDropped = Signal(str)
    clicked = Signal()
    def __init__(self):
        super().__init__(); self.setAcceptDrops(True); self.setMinimumHeight(150); self.setCursor(Qt.PointingHandCursor); self.setObjectName("dropArea")
        layout = QVBoxLayout(self); label = QLabel("DROP MEDIA HERE\n\nor click to choose a video"); label.setAlignment(Qt.AlignCenter); layout.addWidget(label)
    def mousePressEvent(self, event): self.clicked.emit(); super().mousePressEvent(event)
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()
    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls: self.fileDropped.emit(urls[0].toLocalFile()); event.acceptProposedAction()


class SliderRow(QWidget):
    def __init__(self, title, minimum, maximum, value, description=None):
        super().__init__(); self.label = QLabel(title); self.label.setMinimumWidth(118); self.label.setWordWrap(True)
        self.slider = QSlider(Qt.Horizontal); self.slider.setRange(minimum, maximum); self.slider.setValue(value)
        self.spin = QSpinBox(); self.spin.setRange(minimum, maximum); self.spin.setValue(value); self.spin.setMaximumWidth(72)
        row = QHBoxLayout(); row.setContentsMargins(0,0,0,0); row.setSpacing(8); row.addWidget(self.label); row.addWidget(self.slider,1); row.addWidget(self.spin)
        layout = QVBoxLayout(self); layout.setContentsMargins(0,0,0,0); layout.addLayout(row)
        if description:
            note = QLabel(description); note.setObjectName("help"); note.setWordWrap(True); layout.addWidget(note)
        self.slider.valueChanged.connect(self.spin.setValue); self.spin.valueChanged.connect(self.slider.setValue)
    def value(self): return self.spin.value()
    def setValue(self, value): self.spin.setValue(value)


class GhosfWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.media_path = None; self.worker = None; self.processor = None; self.cancel_event = threading.Event(); self.events = WorkerEvents()
        self.setWindowTitle("ghosf"); self.resize(780, 900); self.setMinimumSize(650, 650); self._build_ui(); self._connect_events()

    def _build_ui(self):
        root = QWidget(); self.setCentralWidget(root); layout = QVBoxLayout(root); layout.setContentsMargins(22,22,22,22); layout.setSpacing(12)
        # Header uses a reserved 3/12 + 9/12 grid: identity on the left, media drop on the right.
        header = QGridLayout(); header.setColumnStretch(0,3); header.setColumnStretch(1,9); header.setHorizontalSpacing(18)
        identity = QWidget(); identity_layout = QVBoxLayout(identity); identity_layout.setContentsMargins(0,0,0,0); identity_layout.setSpacing(4)
        title = QLabel("ghosf"); title.setObjectName("title"); title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        subtitle = QLabel("sharp present + previous moments as temporal layers"); subtitle.setObjectName("subtitle"); subtitle.setWordWrap(True); subtitle.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        identity_layout.addWidget(title); identity_layout.addWidget(subtitle); identity_layout.addStretch(1)
        self.drop_area = DropArea(); self.drop_area.fileDropped.connect(self.set_media); self.drop_area.clicked.connect(self.choose_media); self.drop_area.setMinimumHeight(128)
        header.addWidget(identity,0,0); header.addWidget(self.drop_area,0,1)
        layout.addLayout(header)
        self.file_label = QLabel("No media selected."); self.file_label.setObjectName("fileLabel"); self.file_label.setWordWrap(True); layout.addWidget(self.file_label)

        controls = QGridLayout(); controls.setColumnStretch(0,1); controls.setColumnStretch(1,1); controls.setHorizontalSpacing(14)
        temporal = QGroupBox("Temporal Layers"); temporal_layout = QVBoxLayout(temporal)
        self.interval = SliderRow("Ghost frame interval",1,300,1,"How many original frames apart each previous moment is. Does not change output FPS.")
        self.history = SliderRow("Ghost history",1,30,10,"How many previous moments remain visible as layers.")
        temporal_layout.addWidget(self.interval); temporal_layout.addWidget(self.history)
        combo_grid = QGridLayout(); combo_grid.addWidget(QLabel("Blend mode"),0,0)
        self.blend = QComboBox(); self.blend.addItems(["Screen — light accumulates","Normal — transparent layers","Additive — energetic trails"]); combo_grid.addWidget(self.blend,0,1)
        temporal_layout.addLayout(combo_grid)

        appearance = QGroupBox("Ghost Appearance"); appearance_layout = QVBoxLayout(appearance)
        self.contrast = SliderRow("Contrast",-100,100,20,"Extra contrast applied increasingly to older ghost layers.")
        self.shadows = SliderRow("Shadow depth",0,100,15,"Deepens dark areas as a ghost gets older.")
        self.highlights = SliderRow("Highlight intensity",0,100,10,"Pushes light areas as a ghost gets older.")
        self.brightness = SliderRow("Brightness",-100,100,0,"Brightens or darkens older ghost layers.")
        for control in (self.contrast,self.shadows,self.highlights,self.brightness): appearance_layout.addWidget(control)
        controls.addWidget(temporal,0,0); controls.addWidget(appearance,0,1); layout.addLayout(controls)

        fade = QGroupBox("End Fade"); fade_layout = QVBoxLayout(fade); self.end_fade_enabled = QCheckBox("Fade ghost layers before the end"); self.end_fade_enabled.setChecked(True); fade_layout.addWidget(self.end_fade_enabled)
        fade_grid = QGridLayout(); fade_grid.addWidget(QLabel("Fade frames"),0,0); self.fade_frames=QSpinBox(); self.fade_frames.setRange(1,300); self.fade_frames.setValue(20); fade_grid.addWidget(self.fade_frames,0,1)
        fade_grid.addWidget(QLabel("Cubic Bézier"),1,0); self.bezier=QLineEdit(".17,.67,.77,.42"); fade_grid.addWidget(self.bezier,1,1); fade_layout.addLayout(fade_grid); layout.addWidget(fade)

        output = QGroupBox("Output"); output_layout = QGridLayout(output)
        self.output_dir = QLineEdit(str(Path.cwd()/"output")); choose_output=QPushButton("Choose…"); choose_output.clicked.connect(self.choose_output)
        output_layout.addWidget(self.output_dir,0,0,1,2); output_layout.addWidget(choose_output,0,2)
        self.optimize = QCheckBox("Optimize output file"); self.optimize.setToolTip("Use efficient encoding while prioritizing visual quality."); output_layout.addWidget(self.optimize,1,0,1,2)
        output_layout.addWidget(QLabel("Output format"),2,0); self.output_format=QComboBox(); self.output_format.addItems(["MP4","AVI"]); output_layout.addWidget(self.output_format,2,1)
        layout.addWidget(output)

        config = QGroupBox("Configuration Fingerprint"); config_layout = QGridLayout(config)
        config_layout.addWidget(QLabel("Current fingerprint"),0,0); self.config_code=QLineEdit(); self.config_code.setReadOnly(True); config_layout.addWidget(self.config_code,0,1)
        copy_button=QPushButton("Copy"); copy_button.clicked.connect(self.copy_config); config_layout.addWidget(copy_button,0,2)
        config_layout.addWidget(QLabel("Load configuration code"),1,0); self.load_code=QLineEdit(); config_layout.addWidget(self.load_code,1,1)
        load_button=QPushButton("Load"); load_button.clicked.connect(self.load_config); config_layout.addWidget(load_button,1,2); layout.addWidget(config)
        for control in (self.interval.slider,self.interval.spin,self.history.slider,self.history.spin,self.blend,self.end_fade_enabled,self.fade_frames,self.bezier,self.contrast.slider,self.contrast.spin,self.shadows.slider,self.shadows.spin,self.highlights.slider,self.highlights.spin,self.brightness.slider,self.brightness.spin,self.optimize,self.output_format):
            signal = getattr(control,"valueChanged",None) or getattr(control,"currentTextChanged",None) or getattr(control,"textChanged",None) or getattr(control,"stateChanged",None)
            if signal: signal.connect(self.refresh_config_code)

        self.progress=QProgressBar(); self.progress.setRange(0,100); layout.addWidget(self.progress)
        self.status=QLabel("Drop a video to begin."); self.status.setWordWrap(True); layout.addWidget(self.status)
        buttons=QHBoxLayout(); self.process_button=QPushButton("PROCESS MEDIA"); self.process_button.setMinimumHeight(44); self.process_button.clicked.connect(self.start_processing)
        self.cancel_button=QPushButton("CANCEL / ABORT"); self.cancel_button.setMinimumHeight(44); self.cancel_button.setEnabled(False); self.cancel_button.clicked.connect(self.cancel_processing)
        buttons.addWidget(self.process_button,1); buttons.addWidget(self.cancel_button,1); layout.addLayout(buttons)
        self.setStyleSheet("""QWidget { font-size:13px; } QLabel#title { font-size:32px; font-weight:700; } QLabel#subtitle,QLabel#help { color:#777; } QLabel#subtitle { font-size:12px; line-height:1.35; } QLabel#fileLabel { color:#666; } QLabel#help { font-size:11px; margin-left:0px; margin-bottom:4px; } QFrame#dropArea { border:2px dashed #777; border-radius:10px; background:rgba(127,127,127,0.05); } QFrame#dropArea:hover { border-color:#aaa; background:rgba(127,127,127,0.1); } QGroupBox { font-weight:600; margin-top:10px; padding-top:8px; }""")
        self.refresh_config_code()

    def _connect_events(self):
        self.events.progress.connect(self.on_progress); self.events.done.connect(self.on_done); self.events.cancelled.connect(self.on_cancelled); self.events.error.connect(self.on_error)
    def choose_media(self):
        path,_=QFileDialog.getOpenFileName(self,"Choose media","","Video files (*.mp4 *.mov *.mkv *.webm *.avi *.m4v);;All files (*.*)")
        if path: self.set_media(path)
    def set_media(self,path):
        path=Path(path).expanduser().resolve()
        if not path.exists(): QMessageBox.critical(self,"ghosf","That file does not exist."); return
        self.media_path=path; self.file_label.setText(str(path)); self.status.setText("Media selected. Ready to process."); self.progress.setValue(0)
    def choose_output(self):
        path=QFileDialog.getExistingDirectory(self,"Choose output folder")
        if path: self.output_dir.setText(path)
    def settings_from_ui(self):
        try:
            bezier=tuple(float(value.strip()) for value in self.bezier.text().split(","))
            if len(bezier)!=4: raise ValueError
        except ValueError: raise ValueError("Cubic Bézier must contain four numbers, e.g. .17,.67,.77,.42")
        return Settings(ghost_frame_interval=self.interval.value(),ghost_history=self.history.value(),blend_mode=self.blend.currentText().split(" — ",1)[0].lower(),end_fade_enabled=self.end_fade_enabled.isChecked(),end_fade_frames=self.fade_frames.value(),fade_bezier=bezier,ghost_contrast=self.contrast.value(),shadow_depth=self.shadows.value(),highlight_intensity=self.highlights.value(),ghost_brightness=self.brightness.value(),optimize_output=self.optimize.isChecked(),output_format=self.output_format.currentText().lower())
    def refresh_config_code(self,*_):
        try: self.config_code.setText(short_fingerprint(self.settings_from_ui()))
        except ValueError: self.config_code.setText("")
    def copy_config(self):
        QApplication.clipboard().setText(self.config_code.text()); self.status.setText("Short configuration fingerprint copied.")
    def load_config(self):
        try: data=decode_settings(self.load_code.text()); self.interval.setValue(data["i"]); self.history.setValue(data["h"]); mode=data["b"].capitalize(); self.blend.setCurrentIndex({"Screen":0,"Normal":1,"Additive":2}.get(mode,0)); self.end_fade_enabled.setChecked(data["fe"]); self.fade_frames.setValue(data["ff"]); self.bezier.setText(",".join(map(str,data["bz"]))); self.contrast.setValue(data["c"]); self.shadows.setValue(data["s"]); self.highlights.setValue(data["l"]); self.brightness.setValue(data["br"]); self.optimize.setChecked(data["o"]); self.output_format.setCurrentText(data["f"].upper()); self.refresh_config_code(); self.status.setText("Configuration loaded.")
        except Exception as exc: QMessageBox.warning(self,"ghosf",str(exc))
    def start_processing(self):
        if not self.media_path: QMessageBox.warning(self,"ghosf","Drop or choose a media file first."); return
        try: settings=self.settings_from_ui()
        except ValueError as exc: QMessageBox.warning(self,"ghosf",str(exc)); return
        self.cancel_event.clear(); self.process_button.setEnabled(False); self.cancel_button.setEnabled(True); self.progress.setValue(0); self.status.setText("Starting ghosf…")
        self.processor=GhosfProcessor(self.media_path,Path(self.output_dir.text()).expanduser(),settings,self.emit_event,self.cancel_event)
        self.worker=threading.Thread(target=self.run_processor,args=(self.processor,),daemon=True); self.worker.start()
    def cancel_processing(self):
        self.status.setText("Cancelling creation…"); self.cancel_button.setEnabled(False); self.cancel_event.set()
        if self.processor: self.processor.cancel()
    def run_processor(self,processor):
        try: self.events.done.emit(str(processor.run()))
        except ProcessingCancelled: self.events.cancelled.emit()
        except Exception as exc: self.events.error.emit(str(exc))
    def emit_event(self,event):
        if event[0]=="progress": _,percent,message=event; self.events.progress.emit(percent,message)
    def on_progress(self,percent,message): self.progress.setValue(round(percent)); self.status.setText(message)
    def _ready(self): self.process_button.setEnabled(True); self.cancel_button.setEnabled(False); self.processor=None
    def on_done(self,output): self.progress.setValue(100); self.status.setText(f"Done: {output}"); self._ready(); QMessageBox.information(self,"ghosf",f"ghosf complete.\n\n{output}")
    def on_cancelled(self): self.status.setText("Creation cancelled. Temporary files were cleaned up."); self.progress.setValue(0); self._ready()
    def on_error(self,message): self.status.setText("Processing failed."); self._ready(); QMessageBox.critical(self,"ghosf",message)


def main():
    app=QApplication(sys.argv); window=GhosfWindow(); window.show(); sys.exit(app.exec())
if __name__=="__main__": main()
