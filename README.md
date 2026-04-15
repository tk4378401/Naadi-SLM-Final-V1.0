# File: README.md
# Ayurvedic Nadi Pariksha (Pulse Examination) Ecosystem
# आयुर्वेदिक नाडी परीक्षा (नाड़ी परीक्षा) पारिस्थितिकी

A complete, production-ready ecosystem for Ayurvedic pulse diagnosis (Nadi Pariksha) with Python GUI applications and ESP32 firmware.
आयुर्वेदिक नाड़ी निदान (नाडी परीक्षा) के लिए एक पूर्ण, उत्पादन-तैयार पारिस्थितिकी जिसमें Python GUI अनुप्रयोग और ESP32 फ़र्मवेयर शामिल हैं।

## 📋 Table of Contents / विषय सूची

- [System Architecture / प्रणाली वास्तुकला](#system-architecture--प्रणाली-वास्तुकला)
- [DSP Pipeline Explanation / DSP पाइपलाइन स्पष्टीकरण](#dsp-pipeline-explanation--dsp-पाइपलाइन-स्पष्टीकरण)
- [Components / घटक](#components--घटक)
- [Installation / स्थापना](#installation--स्थापना)
- [Usage / उपयोग](#usage--उपयोग)
- [ESP32 Flashing Instructions / ESP32 फ्लैशिंग निर्देश](#esp32-flashing-instructions--esp32-फ्लैशिंग-निर्देश)
- [Critical Notes / महत्वपूर्ण नोट्स](#critical-notes--महत्वपूर्ण-नोट्स)

---

## System Architecture / प्रणाली वास्तुकला

The system consists of three main components:
प्रणाली में तीन मुख्य घटक शामिल हैं:

1. **Nadi_Monitor.py** - Medical Visualizer (TCP Server) / चिकित्सा विज़ुअलाइज़र (TCP सर्वर)
   - Receives pulse data at 1000Hz / 1000Hz पर नाड़ी डेटा प्राप्त करता है
   - Displays Raw, Velocity, and Displacement waveforms / कच्चा, वेग, और विस्थापन तरंग प्रदर्शित करता है
   - PyQt6 GUI with dark theme / डार्क थीम के साथ PyQt6 GUI

2. **Nadi_Generator.py** - Virtual Sensor (TCP Client) / वर्चुअल सेंसर (TCP क्लाइंट)
   - Generates Ayurvedic pulse patterns / आयुर्वेदिक नाड़ी पैटर्न उत्पन्न करता है
   - Four Dosha modes: Vata, Pitta, Kapha, Balanced / चार दोष मोड: वात, पित्त, कफ, संतुलित
   - PyQt6 GUI with Dosha selection buttons / दोष चयन बटन के साथ PyQt6 GUI

3. **ESP32 Firmware** - Hardware Implementation / हार्डवेयर कार्यान्वयन
   - `virtual_dummy.cpp`: Emulator mode / एमुलेटर मोड
   - `hardware_main.cpp`: Real piezo sensor mode / वास्तविक पाईजो सेंसर मोड

---

## DSP Pipeline Explanation / DSP पाइपलाइन स्पष्टीकरण

The DSP engine processes raw acceleration data through a calculus-based pipeline to extract Ayurvedic pulse morphology:
DSP इंजन आयुर्वेदिक नाड़ी रूपात्मकता निकालने के लिए कलन-आधारित पाइपलाइन के माध्यम से कच्चे त्वरण डेटा को संसाधित करता है:

### Calculus Transformation / कलन रूपांतरण

```
Raw Acceleration (त्वरण)
    ↓ [1st-order High-Pass @ 0.1Hz]
Velocity (वेग) = ∫ Raw dt
    ↓ [Leaky Integrate @ 0.999]
    ↓ [1st-order High-Pass @ 0.05Hz]
Displacement (विस्थापन) = ∬ Raw dt²
    ↓ [Invert for VPK analysis]
VPK Morphology (VPK रूपात्मकता)
```

### Waveform Meanings / तरंग रूप का अर्थ

- **Raw (Yellow)**: Acceleration signal from sensor / सेंसर से त्वरण संकेत
- **Velocity (Cyan)**: First integral (∫ Raw dt) - represents pulse speed / पहला इंटीग्रल - नाड़ी गति का प्रतिनिधित्व करता है
- **Displacement (Green)**: Second integral (∬ Raw dt²) - represents Vata/Pitta/Kapha Gati morphology / दूसरा इंटीग्रल - वात/पित्त/कफ गति रूपात्मकता का प्रतिनिधित्व करता है

### Critical Filter Parameters / महत्वपूर्ण फ़िल्टर पैरामीटर

- **Raw High-Pass**: 0.1Hz (preserves 60+ BPM) / 0.1Hz (60+ BPM को संरक्षित करता है)
- **Integrator Anchor**: 0.05Hz (prevents differentiator illusion) / 0.05Hz (विभेदक भ्रम को रोकता है)
- **Leaky Coefficient**: 0.999 (makes Raw/Velocity distinct) / 0.999 (कच्चा/वेग को अलग बनाता है)

---

## Components / घटक

### 1. Nadi_DSP.py / नाडी_DSP.py
Pure mathematical DSP engine shared by Monitor and Generator.
मॉनिटर और जनरेटर द्वारा साझा किया गया शुद्ध गणितीय DSP इंजन।

**Features / विशेषताएं:**
- Pure math operations only (no FFT, no BPM) / केवल शुद्ध गणितीय संचालन (कोई FFT नहीं, कोई BPM नहीं)
- Raw → Velocity → Displacement pipeline / कच्चा → वेग → विस्थापन पाइपलाइन
- Proper state initialization to prevent flatline/spike bugs / फ्लैटलाइन/स्पाइक बग को रोकने के लिए उचित स्थिति आरंभीकरण

### 2. Nadi_Monitor.py / नाडी_मॉनिटर.py
Medical visualizer GUI with real-time plotting.
रियल-टाइम प्लॉटिंग के साथ चिकित्सा विज़ुअलाइज़र GUI।

**Features / विशेषताएं:**
- TCP Server on port 5555 / पोर्ट 5555 पर TCP सर्वर
- 3 stacked plots: Raw (Yellow), Velocity (Cyan), Displacement (Green) / 3 स्टैक्ड प्लॉट: कच्चा (पीला), वेग (सियान), विस्थापन (हरा)
- Auto-range enabled to prevent hidden wave bug / छिपी हुई तरंग बग को रोकने के लिए ऑटो-रेंज सक्षम
- Thread-safe GUI updates via pyqtSignal / pyqtSignal के माध्यम से थ्रेड-सुरक्षित GUI अपडेट

### 3. Nadi_Generator.py / नाडी_जनरेटर.py
Virtual pulse sensor with Dosha selection.
दोष चयन के साथ वर्चुअल नाड़ी सेंसर।

**Features / विशेषताएं:**
- Multi-Gaussian waveform generation / मल्टी-गाऊसीयन तरंग उत्पादन
- 4 Dosha buttons: 🌬 वात (Vata), 🔥 पित्त (Pitta), 💧 कफ (Kapha), ⚖ संतुलित (Balanced) / 4 दोष बटन
- Continuous phase tracking (no sawtooth bug) / निरंतर चरण ट्रैकिंग (कोई sawtooth बग नहीं)
- Auto-reconnect on connection loss / कनेक्शन हानि पर स्वतः-पुनः कनेक्ट

### 4. src/virtual_dummy.cpp / src/virtual_dummy.cpp
ESP32 virtual emulator for testing.
परीक्षण के लिए ESP32 वर्चुअल एमुलेटर।

**Features / विशेषताएं:**
- Simulates pulse data generation / नाड़ी डेटा उत्पादन का सिमुलेशन
- WiFi TCP client / WiFi TCP क्लाइंट
- Continuous phase tracking with fmod() / fmod() के साथ निरंतर चरण ट्रैकिंग
- Auto-reconnect with 2s delay / 2s देरी के साथ स्वतः-पुनः कनेक्ट

### 5. src/hardware_main.cpp / src/hardware_main.cpp
ESP32 real piezo sensor implementation.
ESP32 वास्तविक पाईजो सेंसर कार्यान्वयन।

**Features / विशेषताएं:**
- esp_timer for precise 1000Hz sampling / सटीक 1000Hz सैंपलिंग के लिए esp_timer
- ADC reading from GPIO 34 / GPIO 34 से ADC पढ़ना
- Double-buffered array for ISR / ISR के लिए डबल-बफ़र्ड सरणी
- Auto-reconnect on connection loss / कनेक्शन हानि पर स्वतः-पुनः कनेक्ट

---

## Installation / स्थापना

### Python Dependencies / Python निर्भरताएं

```bash
pip install -r requirements.txt
```

Required packages / आवश्यक पैकेज:
- numpy >= 1.24.0
- scipy >= 1.10.0
- PyQt6 >= 6.4.0
- pyqtgraph >= 0.13.0
- pyinstaller >= 5.13.0

### PlatformIO Setup (for ESP32) / PlatformIO सेटअप (ESP32 के लिए)

```bash
pip install platformio
```

---

## Usage / उपयोग

### Running the Monitor / मॉनिटर चलाना

```bash
python Nadi_Monitor.py
```

The Monitor will start listening on port 5555.
मॉनिटर पोर्ट 5555 पर सुनना शुरू कर देगा।

### Running the Generator / जनरेटर चलाना

```bash
python Nadi_Generator.py
```

Click the Dosha buttons to change pulse patterns.
नाड़ी पैटर्न बदलने के लिए दोष बटन पर क्लिक करें।

### Building Standalone EXEs / स्टैंडअलोन EXE बनाना

```bash
# Build Monitor EXE / मॉनिटर EXE बनाएं
pyinstaller --onefile --windowed --name NadiMonitor Nadi_Monitor.py

# Build Generator EXE / जनरेटर EXE बनाएं
pyinstaller --onefile --windowed --name NadiGenerator Nadi_Generator.py
```

---

## ESP32 Flashing Instructions / ESP32 फ्लैशिंग निर्देश

### 1. Configure WiFi / WiFi कॉन्फ़िगर करें

Edit the appropriate C++ file and update WiFi credentials:
उचित C++ फ़ाइल को संपादित करें और WiFi क्रेडेंशियल अपडेट करें:

```cpp
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
const char* monitor_host = "192.168.1.100"; // Monitor IP address / मॉनिटर IP पता
```

### 2. Build Virtual Emulator Firmware / वर्चुअल एमुलेटर फ़र्मवेयर बनाएं

```bash
pio run -e virtual
```

### 3. Build Hardware Sensor Firmware / हार्डवेयर सेंसर फ़र्मवेयर बनाएं

```bash
pio run -e hardware
```

### 4. Flash to ESP32 / ESP32 पर फ्लैश करें

```bash
# Flash virtual firmware / वर्चुअल फ़र्मवेयर फ्लैश करें
pio run -e virtual --target upload

# Flash hardware firmware / हार्डवेयर फ़र्मवेयर फ्लैश करें
pio run -e hardware --target upload
```

### 5. Monitor Serial Output / सीरियल आउटपुट मॉनिटर करें

```bash
pio device monitor
```

---

## Critical Notes / महत्वपूर्ण नोट्स

### ⚠️ STRICTLY AYURVEDIC - NO FFT, NO BPM
### ⚠️ कड़ाई से आयुर्वेदिक - कोई FFT नहीं, कोई BPM नहीं

This system analyzes **time-domain displacement morphology** (Vata/Pitta/Kapha Gati) only.
यह प्रणाली केवल **समय-डोमेन विस्थापन रूपात्मकता** (वात/पित्त/कफ गति) का विश्लेषण करती है।

**DO NOT:**
- Calculate Beats Per Minute (BPM) / बीट्स पर मिनट (BPM) की गणना न करें
- Use Fast Fourier Transform (FFT) / फास्ट फूरियर ट्रांसफॉर्म (FFT) का उपयोग न करें
- Display frequency-domain graphs / आवृत्ति-डोमेन ग्राफ़ प्रदर्शित न करें
- Use Western allopathic cardiological metrics / पश्चिमी एलोपैथिक कार्डियोलॉजिकल मेट्रिक्स का उपयोग न करें

**DO:**
- Analyze pulse waveform morphology / नाड़ी तरंग रूपात्मकता का विश्लेषण करें
- Study Vata, Pitta, Kapha characteristics / वात, पित्त, कफ विशेषताओं का अध्ययन करें
- Focus on displacement patterns / विस्थापन पैटर्न पर ध्यान केंद्रित करें

### 🔧 Critical Bug Fixes Implemented / कार्यान्वित महत्वपूर्ण बग फिक्स

1. **Continuous Time (Sawtooth Bug Fix)** / निरंतर समय (Sawtooth बग फिक्स)
   - Phase tracking: `phase += freq_hz * dt` (NEVER reset phase) / चरण ट्रैकिंग: `phase += freq_hz * dt` (कभी चरण रीसेट न करें)
   - Beat phase: `fmod(phase, 1.0)` ONLY inside calculation / बीट चरण: केवल गणना के अंदर `fmod(phase, 1.0)`

2. **Differentiator Illusion Fix** / विभेदक भ्रम फिक्स
   - Integrator Anchor filters at 0.05Hz / 0.05Hz पर इंटीग्रेटर एंकर फ़िल्टर
   - Leaky Integrator coefficient at 0.999 / 0.999 पर लीकी इंटीग्रेटर गुणांक

3. **Hidden Wave Fix** / छिपी हुई तरंग फिक्स
   - All plots use `enableAutoRange('y', True)` / सभी प्लॉट `enableAutoRange('y', True)` का उपयोग करते हैं

4. **TCP Data Corruption Fix** / TCP डेटा भ्रष्टाचार फिक्स
   - 4-byte little-endian length header / 4-बाइट लिटिल-एंडियन लंबाई हेडर
   - Exactly 400 bytes payload (50 double samples) / बिल्कुल 400 बाइट्स पेलोड (50 डबल नमूने)
   - `recvall()` helper for complete packet receipt / पूर्ण पैकेट प्राप्ति के लिए `recvall()` सहायक

5. **UI Freeze Fix (Thread Safety)** / UI फ्रीज फिक्स (थ्रेड सुरक्षा)
   - `pyqtSignal(str)` for thread-safe GUI updates / थ्रेड-सुरक्षित GUI अपडेट के लिए `pyqtSignal(str)`
   - Background TCP thread with signal emission / सिग्नल उत्सर्जन के साथ बैकग्राउंड TCP थ्रेड

6. **Flatline/Spike Fix** / फ्लैटलाइन/स्पाइक फिक्स
   - Proper DSP state initialization / उचित DSP स्थिति आरंभीकरण
   - Scale ONLY first High-Pass filter state / केवल पहले हाई-पास फ़िल्टर स्थिति को स्केल करें

7. **Robust TCP & Auto-Reconnect** / मजबूत TCP और स्वतः-पुनः कनेक्ट
   - Try/except in loop with 2s sleep / 2s नींद के साथ लूप में try/except
   - Never crash on ConnectionRefusedError / ConnectionRefusedError पर कभी क्रैश न करें

---

## License / लाइसेंस

This project is for educational and research purposes in Ayurvedic medicine.
यह परियोजना आयुर्वेदिक चिकित्सा में शैक्षिक और अनुसंधान उद्देश्यों के लिए है।

---

## Contact / संपर्क

For questions or contributions, please refer to the project repository.
प्रश्नों या योगदान के लिए, कृपया परियोजना रिपॉजिटरी का संदर्भ लें।

---

**🙏 Namaste / नमस्ते**
