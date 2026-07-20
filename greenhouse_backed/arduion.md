#include "DHT.h"
#include <U8x8lib.h>          // 轻量文本库，几乎不占 RAM

// ========== 引脚定义 ==========
#define SOIL_PIN A0
#define CO2_PIN A3
#define DHT_PIN 13
#define DHT_MODEL DHT11
#define FAN_PIN 5
#define HUMAN_SENSOR 7
#define HUMAN_BEEP 6
#define FLAME_SENSOR 3
#define FLAME_BEEP 2
#define TRIG A1
#define ECHO A2
#define RED_LED 12
#define PUMP_RELAY 8
#define CO2_WARN_LED 9

// 三种模式枚举
#define BEEP_OFF    0
#define BEEP_ON     1
#define BEEP_AUTO   2

// 原有阈值
float tempLimit = 40.0;
int co2WarningThreshold = 700;
const int waterTotalLength = 14;
const unsigned int warmDelay = 2000;
int soilThreshold = 350;
bool pumpManual = false;

// ===== 新增全局阈值 =====
float humiLimit = 70.0;       // 空气湿度阈值
int waterLowThreshold = 20;   // 水位下限报警阈值

byte flameBeepMode = BEEP_AUTO;
byte humanBeepMode = BEEP_AUTO;

DHT dht(DHT_PIN, DHT_MODEL);
unsigned long bootStartTime;
bool fanManualOverride = false;
unsigned long loopCount = 0;

// ---------- OLED 对象（U8x8，无帧缓冲）----------
U8X8_SSD1306_128X64_NONAME_HW_I2C u8x8(/* reset=*/ U8X8_PIN_NONE);

// =========================================================
//  显示函数：每行显示一个数据
// =========================================================
void updateDisplay(float temp, float humi, int soil, int co2, float water) {
  u8x8.clearDisplay();          // 清屏，避免重叠
  u8x8.setCursor(0, 0);
  u8x8.print("Temp:"); u8x8.print(temp, 1); u8x8.print("C");
  u8x8.setCursor(0, 1);
  u8x8.print("Humi:"); u8x8.print(humi, 1); u8x8.print("%");
  u8x8.setCursor(0, 2);
  u8x8.print("Soil:"); u8x8.print(soil);
  u8x8.setCursor(0, 3);
  u8x8.print("CO2:"); u8x8.print(co2);
  u8x8.setCursor(0, 4);
  u8x8.print("Water:"); u8x8.print(water, 0); u8x8.print("%");
}

// =========================================================
//  setup()
// =========================================================
void setup() {
  Serial.begin(9600);
  Serial.println(F("=== 系统启动 ==="));
  bootStartTime = millis();

  pinMode(SOIL_PIN, INPUT);
  pinMode(CO2_PIN, INPUT);
  dht.begin();
  pinMode(FAN_PIN, OUTPUT);
  digitalWrite(FAN_PIN, HIGH);
  pinMode(HUMAN_SENSOR, INPUT);
  pinMode(HUMAN_BEEP, OUTPUT);
  digitalWrite(HUMAN_BEEP, HIGH);
  pinMode(FLAME_SENSOR, INPUT);
  pinMode(FLAME_BEEP, OUTPUT);
  digitalWrite(FLAME_BEEP, HIGH);
  pinMode(TRIG, OUTPUT);
  pinMode(ECHO, INPUT);
  pinMode(RED_LED, OUTPUT);
  digitalWrite(RED_LED, LOW);
  pinMode(PUMP_RELAY, OUTPUT);
  digitalWrite(PUMP_RELAY, LOW);
  pinMode(CO2_WARN_LED, OUTPUT);
  digitalWrite(CO2_WARN_LED, LOW);

  // ---------- OLED 初始化 ----------
  u8x8.begin();
  u8x8.setFont(u8x8_font_chroma48medium8_r);   // 清晰字体
  u8x8.setCursor(0, 0);

  // 打印全部指令说明
  Serial.println(F("=== 指令清单 ==="));
  Serial.println(F("风扇: FAN_ON FAN_OFF FAN_AUTO | GET_TEMP SET_TEMP xx"));
  Serial.println(F("水泵: 1 / 0 / auto"));
  Serial.println(F("CO2: GET_CO2 SET_CO2 xx"));
  Serial.println(F("火焰蜂鸣：FLAME_ON  FLAME_OFF  FLAME_AUTO"));
  Serial.println(F("人体蜂鸣：HUMAN_ON  HUMAN_OFF  HUMAN_AUTO"));
  Serial.println(F("水位指令：GET_WATER  SET_WATER 数值"));
  Serial.println(F("土壤阈值：GET_SOIL   SET_SOIL 数值"));
  Serial.println(F("空气湿度：GET_HUMI   SET_HUMI 数值"));

  Serial.print(F("当前温度阈值: ")); Serial.println(tempLimit);
  Serial.print(F("当前空气湿度阈值: ")); Serial.println(humiLimit);
  Serial.print(F("当前土壤浇水阈值: ")); Serial.println(soilThreshold);
  Serial.print(F("当前水位报警阈值: ")); Serial.println(waterLowThreshold);
}

// =========================================================
//  loop()
// =========================================================
void loop() {
  loopCount++;
  unsigned long now = millis();

  Serial.print(F("[#")); Serial.print(loopCount); Serial.print(F("] "));

  // ---------- 串口指令处理 ----------
  if (Serial.available() > 0) {
    String raw = Serial.readString();
    raw.trim();
    Serial.print(F("收到指令: '")); Serial.print(raw); Serial.println(F("'"));

    // 风扇指令
    if (raw == "FAN_ON") {
      fanManualOverride = true;
      digitalWrite(FAN_PIN, LOW);
      Serial.println(F("-> 风扇开启"));
    }
    else if (raw == "FAN_OFF") {
      fanManualOverride = true;
      digitalWrite(FAN_PIN, HIGH);
      Serial.println(F("-> 风扇关闭"));
    }
    else if (raw == "FAN_AUTO") {
      fanManualOverride = false;
      Serial.println(F("-> 风扇自动温控模式"));
    }
    else if (raw == "GET_TEMP") {
      Serial.print(F("-> 当前温度阈值: ")); Serial.print(tempLimit); Serial.println(F(" °C"));
    }
    else if (raw.startsWith("SET_TEMP ")) {
      String valStr = raw.substring(9);
      valStr.trim();
      float newTemp = valStr.toFloat();
      if (newTemp > 0 && newTemp < 100) {
        tempLimit = newTemp;
        Serial.print(F("-> 温度阈值已设置为 ")); Serial.print(tempLimit); Serial.println(F(" °C"));
      } else {
        Serial.println(F("-> 无效温度值"));
      }
    }
    // CO2指令
    else if (raw == "GET_CO2") {
      Serial.print(F("-> 当前CO2报警阈值: ")); Serial.println(co2WarningThreshold);
    }
    else if (raw.startsWith("SET_CO2 ")) {
      String valStr = raw.substring(8);
      valStr.trim();
      int newCo2 = valStr.toInt();
      if (newCo2 > 0 && newCo2 < 1024) {
        co2WarningThreshold = newCo2;
        Serial.print(F("-> CO2报警阈值已修改为：")); Serial.println(co2WarningThreshold);
      } else {
        Serial.println(F("-> CO2阈值范围：0~1023"));
      }
    }
    // 水泵手动指令
    else if (raw == "1") {
      pumpManual = true;
      digitalWrite(PUMP_RELAY, HIGH);
      Serial.println(F("-> 水泵手动开启浇水"));
    }
    else if (raw == "0") {
      pumpManual = true;
      digitalWrite(PUMP_RELAY, LOW);
      Serial.println(F("-> 水泵手动关闭"));
    }
    else if (raw == "auto") {
      pumpManual = false;
      Serial.println(F("-> 水泵切换湿度自动控制"));
    }
    // 火焰蜂鸣
    else if (raw == "FLAME_ON") {
      flameBeepMode = BEEP_ON;
      digitalWrite(FLAME_BEEP, LOW);
      Serial.println(F("-> 火焰蜂鸣：常开鸣叫"));
    }
    else if (raw == "FLAME_OFF") {
      flameBeepMode = BEEP_OFF;
      digitalWrite(FLAME_BEEP, HIGH);
      Serial.println(F("-> 火焰蜂鸣：静音关闭"));
    }
    else if (raw == "FLAME_AUTO") {
      flameBeepMode = BEEP_AUTO;
      Serial.println(F("-> 火焰蜂鸣：自动模式（明火触发响）"));
    }
    // 人体蜂鸣
    else if (raw == "HUMAN_ON") {
      humanBeepMode = BEEP_ON;
      digitalWrite(HUMAN_BEEP, LOW);
      Serial.println(F("-> 人体蜂鸣：常开鸣叫"));
    }
    else if (raw == "HUMAN_OFF") {
      humanBeepMode = BEEP_OFF;
      digitalWrite(HUMAN_BEEP, HIGH);
      Serial.println(F("-> 人体蜂鸣：静音关闭"));
    }
    else if (raw == "HUMAN_AUTO") {
      humanBeepMode = BEEP_AUTO;
      Serial.println(F("-> 人体蜂鸣：自动模式（人体触发响）"));
    }

    // ========== 新增 水位阈值指令 ==========
    else if (raw == "GET_WATER") {
      Serial.print(F("-> 当前水位报警下限阈值："));
      Serial.print(waterLowThreshold); Serial.println(F(" %"));
    }
    else if (raw.startsWith("SET_WATER ")) {
      String valStr = raw.substring(10);
      valStr.trim();
      int newWaterTh = valStr.toInt();
      if(newWaterTh >= 0 && newWaterTh <= 100)
      {
        waterLowThreshold = newWaterTh;
        Serial.print(F("-> 水位下限阈值设置为："));
        Serial.print(waterLowThreshold); Serial.println(F(" %"));
      }else{
        Serial.println(F("-> 水位阈值合法范围：0~100"));
      }
    }

    // ========== 新增 土壤湿度阈值指令 ==========
    else if (raw == "GET_SOIL") {
      Serial.print(F("-> 当前土壤自动浇水阈值："));
      Serial.println(soilThreshold);
    }
    else if (raw.startsWith("SET_SOIL ")) {
      String valStr = raw.substring(9);
      valStr.trim();
      int newSoilTh = valStr.toInt();
      if(newSoilTh >= 0 && newSoilTh <= 1023)
      {
        soilThreshold = newSoilTh;
        Serial.print(F("-> 土壤浇水阈值修改为："));
        Serial.println(soilThreshold);
      }else{
        Serial.println(F("-> 土壤阈值合法范围：0~1023"));
      }
    }

    // ========== 新增 空气湿度阈值指令 ==========
    else if (raw == "GET_HUMI") {
      Serial.print(F("-> 当前空气湿度报警阈值："));
      Serial.print(humiLimit); Serial.println(F(" %"));
    }
    else if (raw.startsWith("SET_HUMI ")) {
      String valStr = raw.substring(9);
      valStr.trim();
      float newHumiTh = valStr.toFloat();
      if(newHumiTh > 0 && newHumiTh < 100)
      {
        humiLimit = newHumiTh;
        Serial.print(F("-> 空气湿度阈值设置为："));
        Serial.print(humiLimit); Serial.println(F(" %"));
      }else{
        Serial.println(F("-> 空气湿度合法范围：0~100"));
      }
    }

    else {
      Serial.print(F("-> 未知指令: ")); Serial.println(raw);
    }
  }

  // ---------- 读取传感器 ----------
  int soilValue = analogRead(SOIL_PIN);
  int co2Raw = analogRead(CO2_PIN);
  int humanVal = digitalRead(HUMAN_SENSOR);
  int flameVal = digitalRead(FLAME_SENSOR);

  // 超声波测距
  digitalWrite(TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG, LOW);
  long duration = pulseIn(ECHO, HIGH, 100000);
  float distance = -1;
  float waterPercent = 0.0;
  if (duration > 0) {
    distance = duration * 0.034 / 2;
    if (distance > 400) distance = -1;
  }
  if (distance != -1) {
    waterPercent = (waterTotalLength - distance) / waterTotalLength * 100.0;
    if (waterPercent > 100) waterPercent = 100.0;
    if (waterPercent < 0) waterPercent = 0.0;
  }

  float humidity = dht.readHumidity();
  float temp = dht.readTemperature();

  // ---------- 串口打印 ----------
  Serial.print(F("土壤=")); Serial.print(soilValue);
  Serial.print(F(" CO2=")); Serial.print(co2Raw);
  Serial.print(F(" 人体=")); Serial.print(humanVal);
  Serial.print(F(" 火焰=")); Serial.print(flameVal);
  Serial.print(F(" 水位=")); Serial.print(waterPercent,1); Serial.print(F("%"));
  Serial.print(F(" 温度=")); Serial.print(temp); Serial.print(F("℃ 湿度=")); Serial.print(humidity); Serial.println(F("%"));

  // ---------- 火焰蜂鸣 ----------
  if (flameBeepMode == BEEP_ON) {
    digitalWrite(FLAME_BEEP, LOW);
  } else if (flameBeepMode == BEEP_OFF) {
    digitalWrite(FLAME_BEEP, HIGH);
  } else {
    digitalWrite(FLAME_BEEP, (flameVal == LOW) ? LOW : HIGH);
  }

  // ---------- 人体蜂鸣 ----------
  if (humanBeepMode == BEEP_ON) {
    digitalWrite(HUMAN_BEEP, LOW);
  } else if (humanBeepMode == BEEP_OFF) {
    digitalWrite(HUMAN_BEEP, HIGH);
  } else {
    if (now < bootStartTime + warmDelay) {
      digitalWrite(HUMAN_BEEP, HIGH);
    } else {
      digitalWrite(HUMAN_BEEP, (humanVal == HIGH) ? LOW : HIGH);
    }
  }

  // ---------- 缺水红灯 ----------
  if (distance > waterTotalLength && distance != -1) {
    digitalWrite(RED_LED, HIGH);
  } else {
    digitalWrite(RED_LED, LOW);
  }

  // ---------- CO2 黄灯 ----------
  digitalWrite(CO2_WARN_LED, (co2Raw > co2WarningThreshold) ? HIGH : LOW);

  // ---------- 风扇自动温控 ----------
  if (!fanManualOverride) {
    if (isnan(humidity) || isnan(temp)) {
      digitalWrite(FAN_PIN, HIGH);
    } else {
      digitalWrite(FAN_PIN, (temp > tempLimit) ? LOW : HIGH);
    }
  }

  // ---------- 水泵自动控制 ----------
  if (!pumpManual) {
    digitalWrite(PUMP_RELAY, (soilValue < soilThreshold) ? HIGH : LOW);
  }

  // ---------- 刷新 OLED ----------
  updateDisplay(temp, humidity, soilValue, co2Raw, waterPercent);

  delay(1000);
}