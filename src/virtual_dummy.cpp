// File: src/virtual_dummy.cpp
/**
 * ESP32 Virtual Emulator for Ayurvedic Nadi Pariksha
 * आयुर्वेदिक नाडी परीक्षा के लिए ESP32 वर्चुअल एमुलेटर
 * 
 * This file simulates pulse data generation and sends it via TCP
 * यह फ़ाइल नाड़ी डेटा उत्पादन का सिमुलेशन करती है और इसे TCP के माध्यम से भेजती है
 * 
 * CRITICAL: Continuous phase tracking (sawtooth bug fix)
 * महत्वपूर्ण: निरंतर चरण ट्रैकिंग (sawtooth बग फिक्स)
 * - phase += freq_hz * dt (NEVER reset phase)
 * - beat_phase = fmod(phase, 1.0) ONLY inside calculation
 */

#include <WiFi.h>
#include <math.h>

// WiFi Configuration / WiFi कॉन्फ़िगरेशन
const char* ssid = "YOUR_WIFI_SSID";        // Replace with your WiFi SSID / अपना WiFi SSID डालें
const char* password = "YOUR_WIFI_PASSWORD"; // Replace with your WiFi password / अपना WiFi पासवर्ड डालें

// Monitor TCP Configuration / मॉनिटर TCP कॉन्फ़िगरेशन
const char* monitor_host = "192.168.1.100"; // Replace with Monitor IP / मॉनिटर IP डालें
const uint16_t monitor_port = 5555;

// Sampling Configuration / सैंपलिंग कॉन्फ़िगरेशन
const double sample_rate = 1000.0;  // 1000Hz sampling / 1000Hz सैंपलिंग
const double dt = 1.0 / sample_rate; // Time step / समय कदम
const int batch_size = 50;           // Samples per batch / प्रति बैच नमूने

// CRITICAL: Continuous phase tracking (sawtooth bug fix)
// महत्वपूर्ण: निरंतर चरण ट्रैकिंग (sawtooth बग फिक्स)
double phase = 0.0;  // Absolute phase (NEVER reset) / निरपेक्ष चरण (कभी रीसेट न करें)

// Dosha configuration / दोष कॉन्फ़िगरेशन
String current_dosha = "Balanced"; // Default dosha / डिफ़ॉल्ट दोष

/**
 * Generate Gaussian pulse sample
 * गाऊसीयन नाड़ी नमूना उत्पन्न करें
 */
double generate_gaussian_sample(double beat_phase, String dosha) {
    double amplitude;
    double sharpness;
    
    // Dosha-specific parameters / दोष-विशिष्ट पैरामीटर
    if (dosha == "Vata") {
        // Vata: Irregular, fast / वात: अनियमित, तेज़
        amplitude = 1.0;
        sharpness = 0.8;
    } else if (dosha == "Pitta") {
        // Pitta: Regular, sharp / पित्त: नियमित, तीक्ष्ण
        amplitude = 1.2;
        sharpness = 1.5;
    } else if (dosha == "Kapha") {
        // Kapha: Slow, steady / कफ: धीमा, स्थिर
        amplitude = 0.8;
        sharpness = 0.5;
    } else { // Balanced
        // Balanced: Mixed / संतुलित: मिश्रित
        amplitude = 1.0;
        sharpness = 1.0;
    }
    
    // Multi-Gaussian waveform / मल्टी-गाऊसीयन तरंग
    // Primary pulse / प्राथमिक नाड़ी
    double gaussian1 = amplitude * exp(-pow(beat_phase - 0.2, 2) / (2 * pow(0.1 / sharpness, 2)));
    
    // Secondary pulse (dicrotic notch) / द्वितीयक नाड़ी (dicrotic notch)
    double gaussian2 = (amplitude * 0.3) * exp(-pow(beat_phase - 0.5, 2) / (2 * pow(0.08 / sharpness, 2)));
    
    // Tertiary pulse (reflection) / तृतीयक नाड़ी (प्रतिबिंब)
    double gaussian3 = (amplitude * 0.15) * exp(-pow(beat_phase - 0.7, 2) / (2 * pow(0.06 / sharpness, 2)));
    
    return gaussian1 + gaussian2 + gaussian3;
}

/**
 * Generate batch of 50 samples
 * 50 नमूनों का बैच उत्पन्न करें
 */
void generate_batch(double* samples) {
    double base_freq;
    
    // Dosha-specific base frequency / दोष-विशिष्ट आधार आवृत्ति
    if (current_dosha == "Vata") {
        base_freq = 1.4; // ~84 BPM / ~84 BPM
    } else if (current_dosha == "Pitta") {
        base_freq = 1.2; // ~72 BPM / ~72 BPM
    } else if (current_dosha == "Kapha") {
        base_freq = 1.0; // ~60 BPM / ~60 BPM
    } else { // Balanced
        base_freq = 1.15; // ~69 BPM / ~69 BPM
    }
    
    for (int i = 0; i < batch_size; i++) {
        // CRITICAL: Continuous phase tracking (sawtooth bug fix)
        // महत्वपूर्ण: निरंतर चरण ट्रैकिंग (sawtooth बग फिक्स)
        // phase += freq_hz * dt (NEVER reset phase)
        phase += base_freq * dt;
        
        // CRITICAL: Use fmod(phase, 1.0) ONLY here for beat phase
        // महत्वपूर्ण: beat phase के लिए केवल यहां fmod(phase, 1.0) का उपयोग करें
        double beat_phase = fmod(phase, 1.0);
        
        samples[i] = generate_gaussian_sample(beat_phase, current_dosha);
        
        // Add small noise for realism / यथार्थवाद के लिए छोटा शोर जोड़ें
        samples[i] += (double)(esp_random() % 1000) / 50000.0 - 0.01;
    }
}

/**
 * Send batch over TCP
 * बैच को TCP पर भेजें
 */
bool send_batch(WiFiClient& client, double* samples) {
    // CRITICAL: Send 4-byte little-endian length header
    // महत्वपूर्ण: 4-बाइट लिटिल-एंडियन लंबाई हेडर भेजें
    uint32_t length = batch_size * sizeof(double); // 400 bytes / 400 बाइट्स
    client.write((uint8_t*)&length, 4);
    
    // Send payload / पेलोड भेजें
    client.write((uint8_t*)samples, length);
    
    return true;
}

void setup() {
    Serial.begin(115200);
    delay(1000);
    
    Serial.println("ESP32 Virtual Nadi Emulator Starting...");
    Serial.println("ESP32 वर्चुअल नाडी एमुलेटर शुरू हो रहा है...");
    
    // Connect to WiFi / WiFi से कनेक्ट करें
    Serial.print("Connecting to WiFi: ");
    Serial.println(ssid);
    Serial.print("WiFi से कनेक्ट हो रहा है: ");
    Serial.println(ssid);
    
    WiFi.begin(ssid, password);
    
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    
    Serial.println("\n✓ WiFi connected!");
    Serial.println("✓ WiFi कनेक्ट हो गया!");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
    Serial.print("IP पता: ");
    Serial.println(WiFi.localIP());
    
    Serial.println("Virtual emulator ready. Sending to Monitor...");
    Serial.println("वर्चुअल एमुलेटर तैयार। मॉनिटर को भेज रहा है...");
}

void loop() {
    // Create TCP client / TCP क्लाइंट बनाएं
    WiFiClient client;
    
    // Try to connect to Monitor / मॉनिटर से कनेक्ट करने का प्रयास करें
    Serial.print("Connecting to Monitor at ");
    Serial.print(monitor_host);
    Serial.print(":");
    Serial.println(monitor_port);
    
    if (client.connect(monitor_host, monitor_port)) {
        Serial.println("✓ Connected to Monitor!");
        Serial.println("✓ मॉनिटर से कनेक्ट हो गया!");
        
        // Send data loop / डेटा भेजने का लूप
        while (client.connected()) {
            // Generate batch / बैच उत्पन्न करें
            double samples[batch_size];
            generate_batch(samples);
            
            // Send batch / बैच भेजें
            if (!send_batch(client, samples)) {
                Serial.println("✗ Send failed");
                Serial.println("✗ भेजना विफल");
                break;
            }
            
            // Wait 50ms (1000Hz / 50 samples = 50ms per batch)
            // 50ms प्रतीक्षा करें (1000Hz / 50 नमूने = प्रति बैच 50ms)
            delay(50);
        }
        
        // Client disconnected / क्लाइंट डिस्कनेक्ट हो गया
        Serial.println("✗ Disconnected from Monitor");
        Serial.println("✗ मॉनिटर से डिस्कनेक्ट हो गया");
        client.stop();
    } else {
        Serial.println("✗ Connection failed");
        Serial.println("✗ कनेक्शन विफल");
    }
    
    // CRITICAL: Auto-reconnect with 2s delay on connection failure
    // महत्वपूर्ण: कनेक्शन विफलता पर 2s देरी के साथ स्वतः-पुनः कनेक्ट
    Serial.println("Retrying in 2 seconds...");
    Serial.println("2 सेकंड में पुनः प्रयास कर रहा है...");
    delay(2000);
}
