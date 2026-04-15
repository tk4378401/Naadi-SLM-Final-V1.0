// File: src/hardware_main.cpp
/**
 * ESP32 Real Piezo Sensor Implementation for Ayurvedic Nadi Pariksha
 * आयुर्वेदिक नाडी परीक्षा के लिए ESP32 वास्तविक पाईजो सेंसर कार्यान्वयन
 * 
 * This file reads real piezo sensor data via ADC and sends it via TCP
 * यह फ़ाइल ADC के माध्यम से वास्तविक पाईजो सेंसर डेटा पढ़ती है और इसे TCP के माध्यम से भेजती है
 * 
 * CRITICAL: Uses esp_timer for precise 1000Hz sampling
 * महत्वपूर्ण: सटीक 1000Hz सैंपलिंग के लिए esp_timer का उपयोग करता है
 * - ISR triggers every 1000µs (1000Hz)
 * - Double-buffered array to collect 50 samples
 * - Auto-reconnect on connection failure
 */

#include <WiFi.h>
#include <esp_timer.h>
#include <driver/adc.h>

// WiFi Configuration / WiFi कॉन्फ़िगरेशन
const char* ssid = "YOUR_WIFI_SSID";        // Replace with your WiFi SSID / अपना WiFi SSID डालें
const char* password = "YOUR_WIFI_PASSWORD"; // Replace with your WiFi password / अपना WiFi पासवर्ड डालें

// Monitor TCP Configuration / मॉनिटर TCP कॉन्फ़िगरेशन
const char* monitor_host = "192.168.1.100"; // Replace with Monitor IP / मॉनिटर IP डालें
const uint16_t monitor_port = 5555;

// ADC Configuration / ADC कॉन्फ़िगरेशन
const int ADC_PIN = 34;  // GPIO 34 for piezo sensor / पाईजो सेंसर के लिए GPIO 34

// Sampling Configuration / सैंपलिंग कॉन्फ़िगरेशन
const int batch_size = 50;           // Samples per batch / प्रति बैच नमूने
const uint64_t sample_interval_us = 1000; // 1000µs = 1000Hz / 1000µs = 1000Hz

// Double-buffered arrays for ISR / ISR के लिए डबल-बफ़र्ड सरणी
volatile double buffer1[batch_size];
volatile double buffer2[batch_size];
volatile double* active_buffer = buffer1;
volatile double* ready_buffer = nullptr;
volatile int sample_index = 0;
volatile bool batch_ready = false;

// ESP Timer handle / ESP टाइमर हैंडल
esp_timer_handle_t sampling_timer;

// WiFi Client / WiFi क्लाइंट
WiFiClient client;

/**
 * ISR: Timer callback for precise 1000Hz sampling
 * ISR: सटीक 1000Hz सैंपलिंग के लिए टाइमर कॉलबैक
 */
void IRAM_ATTR timer_callback(void* arg) {
    // Read ADC value / ADC मान पढ़ें
    int adc_raw = adc1_get_raw((adc1_channel_t)ADC_PIN);
    
    // Convert to voltage (0-3.3V) and normalize to -1 to 1 range
    // वोल्टेज में बदलें (0-3.3V) और -1 से 1 रेंज में सामान्यीकृत करें
    double voltage = (adc_raw / 4095.0) * 3.3;
    double normalized = (voltage / 1.65) - 1.0;
    
    // Store in active buffer / सक्रिय बफ़र में संग्रहीत करें
    active_buffer[sample_index] = normalized;
    sample_index++;
    
    // Check if batch is complete / जांचें कि बैच पूरा हो गया है
    if (sample_index >= batch_size) {
        // Swap buffers / बफ़र स्वैप करें
        ready_buffer = active_buffer;
        sample_index = 0;
        
        // Switch to other buffer / दूसरे बफ़र पर स्विच करें
        if (active_buffer == buffer1) {
            active_buffer = buffer2;
        } else {
            active_buffer = buffer1;
        }
        
        batch_ready = true;
    }
}

/**
 * Initialize ADC for piezo sensor
 * पाईजो सेंसर के लिए ADC आरंभ करें
 */
void init_adc() {
    // Configure ADC1 / ADC1 कॉन्फ़िगर करें
    adc1_config_width(ADC_WIDTH_BIT_12);
    adc1_config_channel_atten((adc1_channel_t)ADC_PIN, ADC_ATTEN_DB_11);
    
    Serial.println("ADC initialized on GPIO 34");
    Serial.println("GPIO 34 पर ADC आरंभ किया गया");
}

/**
 * Initialize ESP timer for precise sampling
 * सटीक सैंपलिंग के लिए ESP टाइमर आरंभ करें
 */
void init_timer() {
    esp_timer_create_args_t timer_args = {
        .callback = &timer_callback,
        .arg = NULL,
        .dispatch_method = esp_timer_dispatch_t::ESP_TIMER_ISR,
        .name = "sampling_timer"
    };
    
    esp_timer_create(&timer_args, &sampling_timer);
    esp_timer_start_periodic(sampling_timer, sample_interval_us);
    
    Serial.println("Timer initialized for 1000Hz sampling");
    Serial.println("1000Hz सैंपलिंग के लिए टाइमर आरंभ किया गया");
}

/**
 * Send batch over TCP
 * बैच को TCP पर भेजें
 */
bool send_batch(double* samples) {
    if (!client.connected()) {
        return false;
    }
    
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
    
    Serial.println("ESP32 Hardware Nadi Sensor Starting...");
    Serial.println("ESP32 हार्डवेयर नाडी सेंसर शुरू हो रहा है...");
    
    // Initialize ADC / ADC आरंभ करें
    init_adc();
    
    // Initialize timer / टाइमर आरंभ करें
    init_timer();
    
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
    
    Serial.println("Hardware sensor ready. Sending to Monitor...");
    Serial.println("हार्डवेयर सेंसर तैयार। मॉनिटर को भेज रहा है...");
}

void loop() {
    // Try to connect to Monitor / मॉनिटर से कनेक्ट करने का प्रयास करें
    if (!client.connected()) {
        Serial.print("Connecting to Monitor at ");
        Serial.print(monitor_host);
        Serial.print(":");
        Serial.println(monitor_port);
        
        if (client.connect(monitor_host, monitor_port)) {
            Serial.println("✓ Connected to Monitor!");
            Serial.println("✓ मॉनिटर से कनेक्ट हो गया!");
        } else {
            Serial.println("✗ Connection failed");
            Serial.println("✗ कनेक्शन विफल");
            
            // CRITICAL: Auto-reconnect with 2s delay on connection failure
            // महत्वपूर्ण: कनेक्शन विफलता पर 2s देरी के साथ स्वतः-पुनः कनेक्ट
            Serial.println("Retrying in 2 seconds...");
            Serial.println("2 सेकंड में पुनः प्रयास कर रहा है...");
            delay(2000);
            return;
        }
    }
    
    // Wait for batch to be ready from ISR / ISR से बैच तैयार होने की प्रतीक्षा करें
    if (batch_ready && ready_buffer != nullptr) {
        // Copy data from volatile buffer / अस्थिर बफ़र से डेटा कॉपी करें
        double samples[batch_size];
        for (int i = 0; i < batch_size; i++) {
            samples[i] = ready_buffer[i];
        }
        
        // Reset flags / फ्लैग रीसेट करें
        batch_ready = false;
        ready_buffer = nullptr;
        
        // Send batch / बैच भेजें
        if (!send_batch(samples)) {
            Serial.println("✗ Send failed");
            Serial.println("✗ भेजना विफल");
            client.stop();
        }
    }
    
    // Small delay to prevent busy-waiting / व्यस्त-प्रतीक्षा को रोकने के लिए छोटी देरी
    delay(1);
}
