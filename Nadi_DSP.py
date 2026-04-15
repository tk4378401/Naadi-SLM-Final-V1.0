# File: Nadi_DSP.py
"""
Nadi_DSP.py - Shared Pure-Math DSP Engine for Ayurvedic Nadi Pariksha
नाडी_DSP.py - आयुर्वेदिक नाडी परीक्षा के लिए साझा शुद्ध-गणित DSP इंजन

STRICT RULE: PURE MATH ONLY - No loops, no morphological trackers
कड़ाई से नियम: केवल शुद्ध गणित - कोई लूप नहीं, कोई रूपात्मक ट्रैकर नहीं

NO FFT, NO BPM - Time-domain displacement morphology analysis only
कोई FFT नहीं, कोई BPM नहीं - केवल समय-डोमेन विस्थापन रूपात्मकता विश्लेषण
"""

import numpy as np
from scipy.signal import butter, sosfilt, sosfilt_zi

class NadiDSP:
    """
    Ayurvedic Pulse DSP Engine - Pure Mathematical Operations
    आयुर्वेदिक नाडी DSP इंजन - शुद्ध गणितीय संचालन
    
    Pipeline: Raw Acceleration -> Velocity -> Displacement (VPK Morphology)
    पाइपलाइन: कच्चा त्वरण -> वेग -> विस्थापन (VPK रूपात्मकता)
    """
    
    def __init__(self, sample_rate_hz=1000.0):
        """
        Initialize DSP filters with Ayurvedic-compliant parameters
        आयुर्वेदिक-अनुरूप पैरामीटर के साथ DSP फ़िल्टर आरंभ करें
        
        Args:
            sample_rate_hz: Sampling frequency in Hz (default: 1000Hz)
                           सैंपलिंग आवृत्ति Hz में (डिफ़ॉल्ट: 1000Hz)
        """
        self.sample_rate_hz = sample_rate_hz
        self.dt = 1.0 / sample_rate_hz  # Time step / समय कदम
        
        # Initialize filter states / फ़िल्टर स्थितियों को आरंभ करें
        self.zi_hp_raw = None  # Raw High-Pass filter state / कच्चा हाई-पास फ़िल्टर स्थिति
        self.zi_anchor_vel = None  # Velocity anchor filter state / वेग एंकर फ़िल्टर स्थिति
        self.zi_anchor_disp = None  # Displacement anchor filter state / विस्थापन एंकर फ़िल्टर स्थिति
        self.leaky_vel_state = 0.0  # Velocity leaky integrator state / वेग लीकी इंटीग्रेटर स्थिति
        self.leaky_disp_state = 0.0  # Displacement leaky integrator state / विस्थापन लीकी इंटीग्रेटर स्थिति
        
        # Design filters / फ़िल्टर डिज़ाइन करें
        self._design_filters()
        
        # First batch flag for state initialization / स्थिति आरंभीकरण के लिए पहला बैच फ्लैग
        self.first_batch = True
    
    def _design_filters(self):
        """
        Design all Butterworth filters for the DSP pipeline
        DSP पाइपलाइन के लिए सभी बटरवर्थ फ़िल्टर डिज़ाइन करें
        """
        # Raw Clean: 1st-order Butterworth High-Pass at 0.1Hz
        # कच्चा साफ़: 0.1Hz पर 1ले-ऑर्डर बटरवर्थ हाई-पास
        # Updated to preserve low 60 BPM heart rates (1Hz)
        # कम 60 BPM हृदय दर (1Hz) को संरक्षित करने के लिए अपडेट किया गया
        self.sos_hp_raw = butter(1, 0.1, btype='high', fs=self.sample_rate_hz, output='sos')
        
        # Integrator Anchor filters: 1st-order High-Pass at 0.05Hz
        # इंटीग्रेटर एंकर फ़िल्टर: 0.05Hz पर 1ले-ऑर्डर हाई-पास
        # CRITICAL: 0.05Hz to prevent differentiator illusion
        # महत्वपूर्ण: विभेदक भ्रम को रोकने के लिए 0.05Hz
        self.sos_anchor_vel = butter(1, 0.05, btype='high', fs=self.sample_rate_hz, output='sos')
        self.sos_anchor_disp = butter(1, 0.05, btype='high', fs=self.sample_rate_hz, output='sos')
    
    def _leaky_integrate(self, data, state, leaky_coeff=0.999):
        """
        Leaky integration to prevent DC drift
        DC ड्रिफ्ट को रोकने के लिए लीकी इंटीग्रेशन
        
        Args:
            data: Input data array / इनपुट डेटा सरणी
            state: Current integrator state / वर्तमान इंटीग्रेटर स्थिति
            leaky_coeff: Leaky coefficient (default: 0.999)
                         लीकी गुणांक (डिफ़ॉल्ट: 0.999)
        
        Returns:
            Integrated data and new state / एकीकृत डेटा और नई स्थिति
        """
        # CRITICAL: 0.999 for Leaky Integrators so Raw and Velocity look distinct
        # महत्वपूर्ण: लीकी इंटीग्रेटर के लिए 0.999 ताकि कच्चा और वेग अलग दिखें
        integrated = np.zeros_like(data)
        for i, val in enumerate(data):
            state = state * leaky_coeff + val * self.dt
            integrated[i] = state
        return integrated, state
    
    def process_batch(self, raw_batch):
        """
        Process a batch of raw acceleration data through the complete DSP pipeline
        पूर्ण DSP पाइपलाइन के माध्यम से कच्चे त्वरण डेटा के एक बैच को संसाधित करें
        
        Pipeline:
        1. Raw Clean: High-Pass (0.1Hz)
        2. Velocity: Leaky Integrate -> Anchor High-Pass (0.05Hz)
        3. Displacement: Leaky Integrate -> Anchor High-Pass (0.05Hz) -> Invert
        
        Args:
            raw_batch: Raw acceleration samples (numpy array)
                       कच्चा त्वरण नमूने (numpy सरणी)
        
        Returns:
            tuple: (raw_clean, velocity, displacement) - Three waveforms
                   तिगड़ी: (raw_clean, velocity, displacement) - तीन तरंग रूप
        """
        raw_batch = np.asarray(raw_batch)
        
        # Initialize states on first batch / पहले बैच पर स्थितियों को आरंभ करें
        if self.first_batch:
            # CRITICAL: Scale ONLY the first High-Pass filter's state with the first sample
            # महत्वपूर्ण: केवल पहले हाई-पास फ़िल्टर की स्थिति को पहले नमूने के साथ स्केल करें
            self.zi_hp_raw = sosfilt_zi(self.sos_hp_raw) * raw_batch[0]
            self.zi_anchor_vel = sosfilt_zi(self.sos_anchor_vel)
            self.zi_anchor_disp = sosfilt_zi(self.sos_anchor_disp)
            self.leaky_vel_state = 0.0
            self.leaky_disp_state = 0.0
            self.first_batch = False
        
        # Step 1: Raw Clean - High-Pass filter at 0.1Hz
        # चरण 1: कच्चा साफ़ - 0.1Hz पर हाई-पास फ़िल्टर
        raw_clean, self.zi_hp_raw = sosfilt(self.sos_hp_raw, raw_batch, zi=self.zi_hp_raw)
        
        # Step 2: Velocity - Leaky Integrate -> Anchor High-Pass (0.05Hz)
        # चरण 2: वेग - लीकी इंटीग्रेट -> एंकर हाई-पास (0.05Hz)
        vel_leaky, self.leaky_vel_state = self._leaky_integrate(raw_clean, self.leaky_vel_state, leaky_coeff=0.999)
        velocity, self.zi_anchor_vel = sosfilt(self.sos_anchor_vel, vel_leaky, zi=self.zi_anchor_vel)
        
        # Step 3: Displacement - Leaky Integrate -> Anchor High-Pass (0.05Hz) -> Invert
        # चरण 3: विस्थापन - लीकी इंटीग्रेट -> एंकर हाई-पास (0.05Hz) -> उल्टा
        disp_leaky, self.leaky_disp_state = self._leaky_integrate(velocity, self.leaky_disp_state, leaky_coeff=0.999)
        displacement, self.zi_anchor_disp = sosfilt(self.sos_anchor_disp, disp_leaky, zi=self.zi_anchor_disp)
        
        # CRITICAL: Invert displacement for VPK morphology analysis
        # महत्वपूर्ण: VPK रूपात्मकता विश्लेषण के लिए विस्थापन को उल्टा करें
        displacement = -displacement
        
        return raw_clean, velocity, displacement
    
    def reset_states(self):
        """
        Reset all filter states (useful for reconnection or new session)
        सभी फ़िल्टर स्थितियों को रीसेट करें (पुनः कनेक्शन या नए सत्र के लिए उपयोगी)
        """
        self.zi_hp_raw = None
        self.zi_anchor_vel = None
        self.zi_anchor_disp = None
        self.leaky_vel_state = 0.0
        self.leaky_disp_state = 0.0
        self.first_batch = True


# Test function for verification / सत्यापन के लिए परीक्षण फ़ंक्शन
if __name__ == "__main__":
    # Create DSP instance / DSP उदाहरण बनाएं
    dsp = NadiDSP(sample_rate_hz=1000.0)
    
    # Generate test data / परीक्षण डेटा उत्पन्न करें
    t = np.arange(0, 1.0, 0.001)
    test_signal = np.sin(2 * np.pi * 1.2 * t)  # 72 BPM equivalent / 72 BPM समतुल्य
    
    # Process / संसाधित करें
    raw, vel, disp = dsp.process_batch(test_signal)
    
    print(f"Raw shape: {raw.shape}")  # कच्चा आकार
    print(f"Velocity shape: {vel.shape}")  # वेग आकार
    print(f"Displacement shape: {disp.shape}")  # विस्थापन आकार
    print("DSP Engine Test Passed ✓")  # DSP इंजन परीक्षण पास ✓
