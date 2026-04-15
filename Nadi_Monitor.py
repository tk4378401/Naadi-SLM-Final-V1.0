# File: Nadi_Monitor.py
"""
Nadi_Monitor.py - Medical Visualizer / TCP Server for Ayurvedic Nadi Pariksha
नाडी_मॉनिटर.py - आयुर्वेदिक नाडी परीक्षा के लिए चिकित्सा विज़ुअलाइज़र / TCP सर्वर

CRITICAL: PyQt6 GUI Application with Dark Theme
महत्वपूर्ण: डार्क थीम के साथ PyQt6 GUI एप्लिकेशन

NO FFT, NO BPM labels - Time-domain displacement morphology only
कोई FFT, कोई BPM लेबल नहीं - केवल समय-डोमेन विस्थापन रूपात्मकता
"""

import sys
import socket
import struct
import threading
import queue
import time
import numpy as np
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QFrame)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QColor, QPalette
import pyqtgraph as pg

# Import the shared DSP engine / साझा DSP इंजन आयात करें
from Nadi_DSP import NadiDSP


class StatusSignals(QObject):
    """
    Thread-safe signals for updating GUI status labels
    GUI स्थिति लेबल अपडेट करने के लिए थ्रेड-सुरक्षित संकेत
    CRITICAL: Use pyqtSignal to safely update GUI from background thread
    महत्वपूर्ण: बैकग्राउंड थ्रेड से GUI को सुरक्षित रूप से अपडेट करने के लिए pyqtSignal का उपयोग करें
    """
    status_update = pyqtSignal(str)
    connection_update = pyqtSignal(str)


class TCPServerThread(threading.Thread):
    """
    Background TCP server thread for receiving pulse data
    नाड़ी डेटा प्राप्त करने के लिए बैकग्राउंड TCP सर्वर थ्रेड
    """
    
    def __init__(self, host='0.0.0.0', port=5555, data_queue=None, signals=None):
        """
        Initialize TCP server thread / TCP सर्वर थ्रेड आरंभ करें
        """
        super().__init__()
        self.host = host
        self.port = port
        self.data_queue = data_queue
        self.signals = signals
        self.running = True
        self.server_socket = None
        self.client_socket = None
    
    def recvall(self, sock, n):
        """
        CRITICAL: Helper function to receive exactly n bytes
        महत्वपूर्ण: बिल्कुल n बाइट्स प्राप्त करने के लिए सहायक फ़ंक्शन
        
        This prevents TCP data corruption by ensuring complete packet receipt
        यह पूर्ण पैकेट प्राप्ति सुनिश्चित करके TCP डेटा भ्रष्टाचार को रोकता है
        """
        data = bytearray()
        while len(data) < n:
            packet = sock.recv(n - len(data))
            if not packet:
                return None
            data.extend(packet)
        return bytes(data)
    
    def run(self):
        """
        Main TCP server loop / मुख्य TCP सर्वर लूप
        """
        # Create server socket / सर्वर सॉकेट बनाएं
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(1)
            self.signals.status_update.emit(f"✓ Server listening on {self.host}:{self.port}")
            print(f"Server listening on {self.host}:{self.port}")
        except Exception as e:
            self.signals.status_update.emit(f"✗ Bind failed: {str(e)}")
            print(f"Bind failed: {e}")
            return
        
        while self.running:
            try:
                # Accept client connection / क्लाइंट कनेक्शन स्वीकार करें
                self.client_socket, addr = self.server_socket.accept()
                self.signals.connection_update.emit(f"✓ Connected: {addr[0]}:{addr[1]}")
                self.signals.status_update.emit(f"Receiving data from {addr[0]}")
                print(f"Connected to {addr}")
                
                # Receive data loop / डेटा प्राप्त करने का लूप
                while self.running:
                    # CRITICAL: Read 4-byte length header first
                    # महत्वपूर्ण: पहले 4-बाइट लंबाई हेडर पढ़ें
                    length_data = self.recvall(self.client_socket, 4)
                    if length_data is None:
                        break
                    
                    length = struct.unpack('<I', length_data)[0]
                    
                    # CRITICAL: Expect exactly 400 bytes (50 double samples)
                    # महत्वपूर्ण: बिल्कुल 400 बाइट्स की अपेक्षा करें (50 डबल नमूने)
                    if length != 400:
                        print(f"Warning: Expected 400 bytes, got {length}")
                        continue
                    
                    # Read payload / पेलोड पढ़ें
                    payload = self.recvall(self.client_socket, length)
                    if payload is None:
                        break
                    
                    # Unpack 50 double values / 50 डबल मान अनपैक करें
                    samples = struct.unpack('<50d', payload)
                    
                    # Put in queue for GUI processing / GUI प्रसंस्करण के लिए कतार में डालें
                    if self.data_queue:
                        self.data_queue.put(samples)
                
                # Client disconnected / क्लाइंट डिस्कनेक्ट हो गया
                if self.client_socket:
                    self.client_socket.close()
                self.signals.connection_update.emit("✗ Disconnected")
                self.signals.status_update.emit("Waiting for connection...")
                
            except Exception as e:
                print(f"Connection error: {e}")
                if self.client_socket:
                    self.client_socket.close()
                self.signals.connection_update.emit("✗ Error")
                self.signals.status_update.emit(f"Connection error: {str(e)}")
                time.sleep(1)  # Brief pause before retry / पुनः प्रयास से पहले संक्षिप्त विराम
    
    def stop(self):
        """
        Stop the server thread / सर्वर थ्रेड रोकें
        """
        self.running = False
        if self.client_socket:
            self.client_socket.close()
        if self.server_socket:
            self.server_socket.close()


class NadiMonitorWindow(QMainWindow):
    """
    Main Monitor GUI Window / मुख्य मॉनिटर GUI विंडो
    """
    
    def __init__(self):
        super().__init__()
        self.dsp = NadiDSP(sample_rate_hz=1000.0)
        self.data_queue = queue.Queue()
        self.signals = StatusSignals()
        
        # Setup GUI / GUI सेट करें
        self.init_ui()
        
        # Connect signals / संकेतों को कनेक्ट करें
        self.signals.status_update.connect(self.update_status_label)
        self.signals.connection_update.connect(self.update_connection_label)
        
        # Start TCP server / TCP सर्वर प्रारंभ करें
        self.tcp_thread = TCPServerThread(host='0.0.0.0', port=5555, 
                                          data_queue=self.data_queue, 
                                          signals=self.signals)
        self.tcp_thread.start()
        
        # Setup update timer / अपडेट टाइमर सेट करें
        # CRITICAL: 40ms QTimer to drain the entire queue and prevent stutter
        # महत्वपूर्ण: पूरी कतार को खाली करने और हकलाने को रोकने के लिए 40ms QTimer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.process_queue)
        self.update_timer.start(40)  # 25 FPS update rate / 25 FPS अपडेट दर
        
        print("Monitor GUI started ✓")  # मॉनिटर GUI शुरू ✓
    
    def init_ui(self):
        """
        Initialize the GUI layout and styling / GUI लेआउट और स्टाइलिंग आरंभ करें
        """
        self.setWindowTitle("Nadi Monitor - नाडी मॉनिटर (Ayurvedic Pulse Visualizer)")
        self.setGeometry(100, 100, 1200, 900)
        
        # Apply Dark Theme / डार्क थीम लागू करें
        self.apply_dark_theme()
        
        # Main widget and layout / मुख्य विजेट और लेआउट
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Status bar / स्थिति पट्टी
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        status_layout = QHBoxLayout(status_frame)
        
        self.status_label = QLabel("Status: Initializing... / स्थिति: आरंभीकरण...")
        self.status_label.setFont(QFont("Arial", 12))
        self.connection_label = QLabel("Connection: Waiting... / कनेक्शन: प्रतीक्षारत...")
        self.connection_label.setFont(QFont("Arial", 12))
        
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.connection_label)
        
        layout.addWidget(status_frame)
        
        # CRITICAL: 3 stacked pg.PlotWidget plots / 3 स्टैक्ड pg.PlotWidget प्लॉट
        # Plot 1: Raw Pulse (Acceleration) - Yellow / प्लॉट 1: कच्चा नाड़ी (त्वरण) - पीला
        self.plot_raw = pg.PlotWidget(title="Raw Pulse (Acceleration) - कच्चा नाड़ी (त्वरण)")
        self.plot_raw.setBackground('k')
        self.plot_raw.showGrid(x=True, y=True, alpha=0.3)
        self.plot_raw.setYRange(-2, 2)
        self.curve_raw = self.plot_raw.plot(pen='y', width=2)
        # CRITICAL: enableAutoRange to prevent hidden wave bug
        # महत्वपूर्ण: छिपी हुई तरंग बग को रोकने के लिए enableAutoRange
        self.plot_raw.enableAutoRange('y', True)
        layout.addWidget(self.plot_raw)
        
        # Plot 2: Velocity (∫ Raw dt) - Cyan / प्लॉट 2: वेग (∫ कच्चा dt) - सियान
        self.plot_vel = pg.PlotWidget(title="Velocity (∫ Raw dt) - वेग (∫ कच्चा dt)")
        self.plot_vel.setBackground('k')
        self.plot_vel.showGrid(x=True, y=True, alpha=0.3)
        self.plot_vel.setYRange(-1, 1)
        self.curve_vel = self.plot_vel.plot(pen='c', width=2)
        # CRITICAL: enableAutoRange to prevent hidden wave bug
        # महत्वपूर्ण: छिपी हुई तरंग बग को रोकने के लिए enableAutoRange
        self.plot_vel.enableAutoRange('y', True)
        layout.addWidget(self.plot_vel)
        
        # Plot 3: Displacement (∬ Raw dt² - VPK Morphology) - Green
        # प्लॉट 3: विस्थापन (∬ कच्चा dt² - VPK रूपात्मकता) - हरा
        self.plot_disp = pg.PlotWidget(title="Displacement (∬ Raw dt² - VPK Morphology) - विस्थापन (∬ कच्चा dt² - VPK रूपात्मकता)")
        self.plot_disp.setBackground('k')
        self.plot_disp.showGrid(x=True, y=True, alpha=0.3)
        self.plot_disp.setYRange(-0.5, 0.5)
        self.curve_disp = self.plot_disp.plot(pen='g', width=2)
        # CRITICAL: enableAutoRange to prevent hidden wave bug
        # महत्वपूर्ण: छिपी हुई तरंग बग को रोकने के लिए enableAutoRange
        self.plot_disp.enableAutoRange('y', True)
        layout.addWidget(self.plot_disp)
        
        # Info label / जानकारी लेबल
        info_label = QLabel("📊 Ayurvedic Nadi Pariksha - Vata/Pitta/Kapha Gati Analysis | आयुर्वेदिक नाडी परीक्षा - वात/पित्त/कफ गति विश्लेषण")
        info_label.setFont(QFont("Arial", 10))
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)
    
    def apply_dark_theme(self):
        """
        Apply dark theme to the application / एप्लिकेशन पर डार्क थीम लागू करें
        """
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(40, 40, 40))
        palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Button, QColor(45, 45, 45))
        palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
        QApplication.setPalette(palette)
    
    def update_status_label(self, text):
        """
        Update status label (thread-safe via signal) / स्थिति लेबल अपडेट करें (संकेत के माध्यम से थ्रेड-सुरक्षित)
        """
        self.status_label.setText(f"Status: {text}")
    
    def update_connection_label(self, text):
        """
        Update connection label (thread-safe via signal) / कनेक्शन लेबल अपडेट करें (संकेत के माध्यम से थ्रेड-सुरक्षित)
        """
        self.connection_label.setText(f"Connection: {text}")
    
    def process_queue(self):
        """
        Process all data in the queue to prevent stutter
        हकलाने को रोकने के लिए कतार में सभी डेटा को संसाधित करें
        
        CRITICAL: Drain the ENTIRE queue using while not queue.empty()
        महत्वपूर्ण: while not queue.empty() का उपयोग करके पूरी कतार खाली करें
        """
        # Process all available batches / सभी उपलब्ध बैच को संसाधित करें
        while not self.data_queue.empty():
            try:
                samples = self.data_queue.get_nowait()
                
                # Process through DSP pipeline / DSP पाइपलाइन के माध्यम से संसाधित करें
                raw_clean, velocity, displacement = self.dsp.process_batch(samples)
                
                # Update plots / प्लॉट अपडेट करें
                self.curve_raw.setData(raw_clean)
                self.curve_vel.setData(velocity)
                self.curve_disp.setData(displacement)
                
            except queue.Empty:
                break
    
    def closeEvent(self, event):
        """
        Handle window close event / विंडो बंद करने की घटना संभालें
        """
        # Stop TCP thread / TCP थ्रेड रोकें
        if self.tcp_thread:
            self.tcp_thread.stop()
            self.tcp_thread.join(timeout=2)
        
        # Stop update timer / अपडेट टाइमर रोकें
        self.update_timer.stop()
        
        print("Monitor GUI closed ✓")  # मॉनिटर GUI बंद ✓
        event.accept()


def main():
    """
    Main entry point / मुख्य प्रवेश बिंदु
    """
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = NadiMonitorWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
