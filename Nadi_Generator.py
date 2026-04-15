# File: Nadi_Generator.py
"""
Nadi_Generator.py - Python Virtual Sensor / TCP Client for Ayurvedic Nadi Pariksha
नाडी_जनरेटर.py - आयुर्वेदिक नाडी परीक्षा के लिए Python वर्चुअल सेंसर / TCP क्लाइंट

CRITICAL: PyQt6 GUI Application with Dark Theme
महत्वपूर्ण: डार्क थीम के साथ PyQt6 GUI एप्लिकेशन

MUST include 4 Dosha buttons with EXACT labels:
अवश्य 4 दोष बटन शामिल करें जिनमें सटीक लेबल हों:
🌬 वात (Vata), 🔥 पित्त (Pitta), 💧 कफ (Kapha), ⚖ संतुलित (Balanced)
"""

import sys
import socket
import struct
import threading
import time
import numpy as np
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QFrame, QLineEdit)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QColor, QPalette


class StatusSignals(QObject):
    """
    Thread-safe signals for updating GUI status labels
    GUI स्थिति लेबल अपडेट करने के लिए थ्रेड-सुरक्षित संकेत
    CRITICAL: Use pyqtSignal to safely update GUI from background thread
    महत्वपूर्ण: बैकग्राउंड थ्रेड से GUI को सुरक्षित रूप से अपडेट करने के लिए pyqtSignal का उपयोग करें
    """
    status_update = pyqtSignal(str)


class TCPClientThread(threading.Thread):
    """
    Background TCP client thread for sending pulse data
    नाड़ी डेटा भेजने के लिए बैकग्राउंड TCP क्लाइंट थ्रेड
    """
    
    def __init__(self, host='127.0.0.1', port=5555, signals=None):
        """
        Initialize TCP client thread / TCP क्लाइंट थ्रेड आरंभ करें
        """
        super().__init__()
        self.host = host
        self.port = port
        self.signals = signals
        self.running = True
        self.client_socket = None
        self.current_dosha = "Balanced"  # Default dosha / डिफ़ॉल्ट दोष
        
        # CRITICAL: Continuous phase tracking (sawtooth bug fix)
        # महत्वपूर्ण: निरंतर चरण ट्रैकिंग (sawtooth बग फिक्स)
        self.phase = 0.0  # Absolute phase / निरपेक्ष चरण
        self.sample_rate = 1000.0  # 1000Hz / 1000Hz
        self.dt = 1.0 / self.sample_rate
    
    def recvall(self, sock, n):
        """
        Helper function to receive exactly n bytes
        बिल्कुल n बाइट्स प्राप्त करने के लिए सहायक फ़ंक्शन
        """
        data = bytearray()
        while len(data) < n:
            packet = sock.recv(n - len(data))
            if not packet:
                return None
            data.extend(packet)
        return bytes(data)
    
    def generate_multi_gaussian_batch(self, dosha):
        """
        Generate 50 samples using Multi-Gaussian waveform based on Dosha
        दोष के आधार पर मल्टी-गाऊसीयन तरंग का उपयोग करके 50 नमूने उत्पन्न करें
        
        Dosha characteristics / दोष विशेषताएं:
        - Vata (वात): Irregular, fast, variable frequency
        - Pitta (पित्त): Regular, sharp, medium frequency
        - Kapha (कफ): Slow, steady, low frequency
        - Balanced (संतुलित): Balanced waveform
        """
        samples = np.zeros(50)
        
        # Dosha-specific parameters / दोष-विशिष्ट पैरामीटर
        if dosha == "Vata":
            # Vata: Irregular, fast (80-100 BPM equivalent)
            # वात: अनियमित, तेज़ (80-100 BPM समतुल्य)
            base_freq = 1.4  # ~84 BPM
            freq_variation = 0.3
            amplitude = 1.0
            sharpness = 0.8
        elif dosha == "Pitta":
            # Pitta: Regular, sharp (70-80 BPM equivalent)
            # पित्त: नियमित, तीक्ष्ण (70-80 BPM समतुल्य)
            base_freq = 1.2  # ~72 BPM
            freq_variation = 0.05
            amplitude = 1.2
            sharpness = 1.5
        elif dosha == "Kapha":
            # Kapha: Slow, steady (60-70 BPM equivalent)
            # कफ: धीमा, स्थिर (60-70 BPM समतुल्य)
            base_freq = 1.0  # ~60 BPM
            freq_variation = 0.02
            amplitude = 0.8
            sharpness = 0.5
        else:  # Balanced
            # Balanced: Mixed characteristics (70-75 BPM equivalent)
            # संतुलित: मिश्रित विशेषताएं (70-75 BPM समतुल्य)
            base_freq = 1.15  # ~69 BPM
            freq_variation = 0.1
            amplitude = 1.0
            sharpness = 1.0
        
        # Generate 50 samples / 50 नमूने उत्पन्न करें
        for i in range(50):
            # CRITICAL: Continuous phase tracking (sawtooth bug fix)
            # महत्वपूर्ण: निरंतर चरण ट्रैकिंग (sawtooth बग फिक्स)
            # phase += freq_hz * dt (NEVER reset phase)
            # beat_phase = phase % 1.0 ONLY inside calculation
            self.phase += base_freq * self.dt
            
            # Add frequency variation for Vata / वात के लिए आवृत्ति विविधता जोड़ें
            if dosha == "Vata":
                freq_mod = base_freq + freq_variation * np.sin(2 * np.pi * 0.5 * i * self.dt)
                self.phase += (freq_mod - base_freq) * self.dt
            
            # CRITICAL: Use beat_phase = phase % 1.0 ONLY here
            # महत्वपूर्ण: beat_phase = phase % 1.0 का उपयोग केवल यहां करें
            beat_phase = self.phase % 1.0
            
            # Multi-Gaussian waveform / मल्टी-गाऊसीयन तरंग
            # Primary pulse / प्राथमिक नाड़ी
            gaussian1 = amplitude * np.exp(-((beat_phase - 0.2) ** 2) / (2 * (0.1 / sharpness) ** 2))
            
            # Secondary pulse (dicrotic notch simulation) / द्वितीयक नाड़ी (dicrotic notch सिमुलेशन)
            gaussian2 = (amplitude * 0.3) * np.exp(-((beat_phase - 0.5) ** 2) / (2 * (0.08 / sharpness) ** 2))
            
            # Tertiary pulse (reflection) / तृतीयक नाड़ी (प्रतिबिंब)
            gaussian3 = (amplitude * 0.15) * np.exp(-((beat_phase - 0.7) ** 2) / (2 * (0.06 / sharpness) ** 2))
            
            samples[i] = gaussian1 + gaussian2 + gaussian3
            
            # Add small noise for realism / यथार्थवाद के लिए छोटा शोर जोड़ें
            samples[i] += np.random.normal(0, 0.02)
        
        return samples
    
    def run(self):
        """
        Main TCP client loop with auto-reconnect
        स्वतः-पुनः कनेक्ट के साथ मुख्य TCP क्लाइंट लूप
        """
        while self.running:
            try:
                # Create socket / सॉकेट बनाएं
                self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.client_socket.connect((self.host, self.port))
                self.signals.status_update.emit(f"✓ Connected to {self.host}:{self.port}")
                print(f"Connected to {self.host}:{self.port}")
                
                # Send data loop / डेटा भेजने का लूप
                while self.running:
                    # Generate batch of 50 samples / 50 नमूनों का बैच उत्पन्न करें
                    samples = self.generate_multi_gaussian_batch(self.current_dosha)
                    
                    # CRITICAL: Convert to float64 and pack
                    # महत्वपूर्ण: float64 में बदलें और पैक करें
                    samples_float64 = np.array(samples, dtype=np.float64)
                    payload = struct.pack('<50d', *samples_float64)
                    
                    # CRITICAL: Send 4-byte length header + 400 bytes payload
                    # महत्वपूर्ण: 4-बाइट लंबाई हेडर + 400 बाइट पेलोड भेजें
                    length = len(payload)
                    header = struct.pack('<I', length)
                    self.client_socket.sendall(header + payload)
                    
                    # Wait 50ms (1000Hz / 50 samples = 50ms per batch)
                    # 50ms प्रतीक्षा करें (1000Hz / 50 नमूने = प्रति बैच 50ms)
                    time.sleep(0.05)
                
            except (ConnectionRefusedError, ConnectionResetError, OSError) as e:
                # CRITICAL: NEVER crash on connection errors, auto-reconnect with 2s sleep
                # महत्वपूर्ण: कनेक्शन त्रुटियों पर कभी भी क्रैश न करें, 2s नींद के साथ स्वतः-पुनः कनेक्ट करें
                self.signals.status_update.emit(f"✗ Connection lost: {str(e)}. Retrying in 2s...")
                print(f"Connection lost: {e}. Retrying in 2s...")
                if self.client_socket:
                    self.client_socket.close()
                time.sleep(2)  # Wait 2s before retry / पुनः प्रयास से पहले 2s प्रतीक्षा करें
            except Exception as e:
                self.signals.status_update.emit(f"✗ Error: {str(e)}")
                print(f"Error: {e}")
                if self.client_socket:
                    self.client_socket.close()
                time.sleep(2)
    
    def set_dosha(self, dosha):
        """
        Set the current dosha for waveform generation
        तरंग उत्पादन के लिए वर्तमान दोष सेट करें
        """
        self.current_dosha = dosha
        print(f"Dosha changed to: {dosha}")  # दोष बदला: {dosha}
    
    def stop(self):
        """
        Stop the client thread / क्लाइंट थ्रेड रोकें
        """
        self.running = False
        if self.client_socket:
            self.client_socket.close()


class NadiGeneratorWindow(QMainWindow):
    """
    Main Generator GUI Window / मुख्य जनरेटर GUI विंडो
    """
    
    def __init__(self):
        super().__init__()
        
        # Setup GUI / GUI सेट करें
        self.init_ui()
        
        # Connect signals / संकेतों को कनेक्ट करें
        self.signals = StatusSignals()
        self.signals.status_update.connect(self.update_status_label)
        
        # Start TCP client / TCP क्लाइंट प्रारंभ करें
        self.tcp_thread = TCPClientThread(host='127.0.0.1', port=5555, signals=self.signals)
        self.tcp_thread.start()
        
        print("Generator GUI started ✓")  # जनरेटर GUI शुरू ✓
    
    def init_ui(self):
        """
        Initialize the GUI layout and styling / GUI लेआउट और स्टाइलिंग आरंभ करें
        """
        self.setWindowTitle("Nadi Generator - नाडी जनरेटर (Ayurvedic Pulse Simulator)")
        self.setGeometry(150, 150, 800, 600)
        
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
        
        self.status_label = QLabel("Status: Connecting... / स्थिति: कनेक्ट हो रहा है...")
        self.status_label.setFont(QFont("Arial", 12))
        
        status_layout.addWidget(self.status_label)
        layout.addWidget(status_frame)
        
        # IP Address input / IP पता इनपुट
        ip_frame = QFrame()
        ip_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        ip_layout = QHBoxLayout(ip_frame)
        
        ip_label = QLabel("Monitor IP: / मॉनिटर IP:")
        ip_label.setFont(QFont("Arial", 11))
        self.ip_input = QLineEdit("127.0.0.1")
        self.ip_input.setFont(QFont("Arial", 11))
        
        reconnect_btn = QPushButton("Reconnect / पुनः कनेक्ट करें")
        reconnect_btn.setFont(QFont("Arial", 11))
        reconnect_btn.clicked.connect(self.reconnect)
        
        ip_layout.addWidget(ip_label)
        ip_layout.addWidget(self.ip_input)
        ip_layout.addWidget(reconnect_btn)
        layout.addWidget(ip_frame)
        
        # CRITICAL: 4 Dosha buttons with EXACT labels
        # महत्वपूर्ण: सटीक लेबल के साथ 4 दोष बटन
        dosha_frame = QFrame()
        dosha_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        dosha_layout = QVBoxLayout(dosha_frame)
        
        dosha_title = QLabel("Select Dosha Pattern / दोष पैटर्न चुनें:")
        dosha_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        dosha_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dosha_layout.addWidget(dosha_title)
        
        # Button layout / बटन लेआउट
        button_layout = QHBoxLayout()
        
        # Button 1: Vata / वात
        self.btn_vata = QPushButton("🌬 वात (Vata)")
        self.btn_vata.setFont(QFont("Arial", 14))
        self.btn_vata.setMinimumHeight(80)
        self.btn_vata.setStyleSheet("""
            QPushButton {
                background-color: #8B4513;
                color: white;
                border: 2px solid #654321;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #A0522D;
            }
            QPushButton:pressed {
                background-color: #654321;
            }
        """)
        self.btn_vata.clicked.connect(lambda: self.set_dosha("Vata"))
        button_layout.addWidget(self.btn_vata)
        
        # Button 2: Pitta / पित्त
        self.btn_pitta = QPushButton("🔥 पित्त (Pitta)")
        self.btn_pitta.setFont(QFont("Arial", 14))
        self.btn_pitta.setMinimumHeight(80)
        self.btn_pitta.setStyleSheet("""
            QPushButton {
                background-color: #DC143C;
                color: white;
                border: 2px solid #8B0000;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #FF6347;
            }
            QPushButton:pressed {
                background-color: #8B0000;
            }
        """)
        self.btn_pitta.clicked.connect(lambda: self.set_dosha("Pitta"))
        button_layout.addWidget(self.btn_pitta)
        
        # Button 3: Kapha / कफ
        self.btn_kapha = QPushButton("💧 कफ (Kapha)")
        self.btn_kapha.setFont(QFont("Arial", 14))
        self.btn_kapha.setMinimumHeight(80)
        self.btn_kapha.setStyleSheet("""
            QPushButton {
                background-color: #4682B4;
                color: white;
                border: 2px solid #2F4F4F;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #5F9EA0;
            }
            QPushButton:pressed {
                background-color: #2F4F4F;
            }
        """)
        self.btn_kapha.clicked.connect(lambda: self.set_dosha("Kapha"))
        button_layout.addWidget(self.btn_kapha)
        
        # Button 4: Balanced / संतुलित
        self.btn_balanced = QPushButton("⚖ संतुलित (Balanced)")
        self.btn_balanced.setFont(QFont("Arial", 14))
        self.btn_balanced.setMinimumHeight(80)
        self.btn_balanced.setStyleSheet("""
            QPushButton {
                background-color: #228B22;
                color: white;
                border: 2px solid #006400;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #32CD32;
            }
            QPushButton:pressed {
                background-color: #006400;
            }
        """)
        self.btn_balanced.clicked.connect(lambda: self.set_dosha("Balanced"))
        button_layout.addWidget(self.btn_balanced)
        
        dosha_layout.addLayout(button_layout)
        layout.addWidget(dosha_frame)
        
        # Info label / जानकारी लेबल
        info_label = QLabel("🎯 Generates Ayurvedic pulse patterns at 1000Hz sampling rate | आयुर्वेदिक नाड़ी पैटर्न 1000Hz सैंपलिंग दर पर उत्पन्न करता है")
        info_label.setFont(QFont("Arial", 10))
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)
        
        layout.addStretch()
    
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
    
    def set_dosha(self, dosha):
        """
        Set the dosha pattern / दोष पैटर्न सेट करें
        """
        if self.tcp_thread:
            self.tcp_thread.set_dosha(dosha)
            self.status_label.setText(f"Status: Dosha set to {dosha} / दोष सेट: {dosha}")
    
    def reconnect(self):
        """
        Reconnect to the monitor / मॉनिटर से पुनः कनेक्ट करें
        """
        # Stop current thread / वर्तमान थ्रेड रोकें
        if self.tcp_thread:
            self.tcp_thread.stop()
            self.tcp_thread.join(timeout=2)
        
        # Get new IP / नया IP प्राप्त करें
        new_host = self.ip_input.text()
        
        # Start new thread / नया थ्रेड प्रारंभ करें
        self.tcp_thread = TCPClientThread(host=new_host, port=5555, signals=self.signals)
        self.tcp_thread.start()
    
    def closeEvent(self, event):
        """
        Handle window close event / विंडो बंद करने की घटना संभालें
        """
        # Stop TCP thread / TCP थ्रेड रोकें
        if self.tcp_thread:
            self.tcp_thread.stop()
            self.tcp_thread.join(timeout=2)
        
        print("Generator GUI closed ✓")  # जनरेटर GUI बंद ✓
        event.accept()


def main():
    """
    Main entry point / मुख्य प्रवेश बिंदु
    """
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = NadiGeneratorWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
