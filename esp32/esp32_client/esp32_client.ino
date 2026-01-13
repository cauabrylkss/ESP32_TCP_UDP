#include <WiFi.h>
#include <ArduinoJson.h>

/// wifi
const char* ssid = "RA3";
const char* password = "1234";

/// servidor tcp
const char* serverIP = "192.168.0.100";  
const uint16_t serverPort = 5000;

WiFiClient client;//crizaçao de objeto wificlient representando socket do esp32

/// led
const int LED_PIN = 2;    //constante do pino do LED (GPIO 2).

/// tempo
unsigned long lastSend = 0;  //ultima vez qm que eniou os dados
const unsigned long interval = 2000;    //intervalo entre envios

void connectWiFi() {
  Serial.print("Conectando ao WiFi "); //escreve mesnagens ao monitor serial
  Serial.println(ssid);

  WiFi.begin(ssid, password);  //inicia a conexao wifi

  while (WiFi.status() != WL_CONNECTED) {
    Serial.print(".");  // espera ate a conexao ser estabelecida
    delay(500);
  }

  Serial.println("\nWiFi conectado!");
  Serial.print("IP local: ");
  Serial.println(WiFi.localIP());
}

void connectServer() {
  Serial.print("Conectando ao servidor TCP... ");

  while (!client.connect(serverIP, serverPort)) {  //tenta abrir conexao tcp e retorna true
    Serial.print(".");
    delay(500);
  }

  Serial.println("\nConectado ao servidor!");
}

void sendSensorData() {
  StaticJsonDocument<200> doc; //cria um documento JSON em memoria (200 bytes reservados)

  doc["type"] = "data";  //adiciona campos ao JSON,dados simulados
  doc["from"] = "esp32";

  JsonObject payload = doc.createNestedObject("payload");  //cria um objeto interno chamado payload
  payload["temp"] = 25.3;        //adiciona os valores dos dados simulados
  payload["hum"] = 60;           

  String json;
  serializeJson(doc, json); //converte o JSON para string

  client.println(json);  

  Serial.print("Enviado: ");
  Serial.println(json);
}

void processCommand(String cmd) {  // remove espaços e quebras no começo/fim
  cmd.trim();
  if (cmd.length() == 0) return;

  Serial.print("Comando recebido: ");
  Serial.println(cmd);

  if (cmd == "led_on") { //seta o pino do led para HIGH e envia um ACK em JSON
    digitalWrite(LED_PIN, HIGH);
    client.println("{\"ack\":\"led_on\"}");
    Serial.println("LED ligado!");
  }
  else if (cmd == "led_off") {  //desliga o led
    digitalWrite(LED_PIN, LOW);
    client.println("{\"ack\":\"led_off\"}");
    Serial.println("LED desligado!");
  }
}

void setup() {
  Serial.begin(115200); //inicializa o monitor serial (baud 115200)

  pinMode(LED_PIN, OUTPUT);  //configura o pino do LED como saida
  digitalWrite(LED_PIN, LOW);  //garante que o led começe desligado
  connectWiFi();  //chama a funçao para conectar ao wifi
  connectServer();  //chama a funçao para conectar ao servidor TCP
}

void loop() {

  /// reconexão
  if (!client.connected()) {  //verifica se o socket TCP esta conectado
    Serial.println("Conexão perdida! Tentando reconectar...");
    client.stop();
    delay(1000);
    connectServer();
  }

  /// envio de json
  unsigned long now = millis();  //pega tempo em ms desde o boot
  if (now - lastSend >= interval) {  //atualiza lastsend e chama sendsensordata() para enviar o JSON
    lastSend = now;
    sendSensorData();
  }

  /// comandos vindo do server
  while (client.available()) {
    String msg = client.readStringUntil('\n');
    processCommand(msg);  //trata o comando lido (liga,desliga LED ou ignora)
  }
}
