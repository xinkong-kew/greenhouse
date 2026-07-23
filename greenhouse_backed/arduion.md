#include "DHT.h"
#include <U8x8lib.h>
#include <Servo.h>

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
#define SERVO_PIN 10

// 三种模式枚举
#define BEEP_OFF    0
#define BEEP_ON     1
#define BEEP_AUTO   2

// 阈值变量
float tempLimit = 30.0;        // 西红柿：超过30°C风扇开启降温
int co2WarningThreshold = 700;
const int waterTotalLength = 14;
const unsigned int warmDelay = 2000;
int soilThreshold = 60;        // 西红柿：土壤低于60%开始浇水（保持60-80%）
bool pumpManual = false;
float humiLimit = 80.0;        // 西红柿：超过80%湿度需排湿防病
int waterLowThreshold = 20;

byte flameBeepMode = BEEP_AUTO;
byte humanBeepMode = BEEP_AUTO;

DHT dht(DHT_PIN, DHT_MODEL);
unsigned long bootStartTime;
bool fanManualOverride = false;
unsigned long loopCount = 0;

Servo myServo;
bool servoAutoMode = false;       // 默认手动模式，发送 SERVO_AUTO 后开启自动
int lastServoAngle = -1;

U8X8_SSD1306_128X64_NONAME_SW_I2C u8x8(A5, A4, U8X8_PIN_NONE);

// =========================================================
//  显示函数
// =========================================================
void updateDisplay(float temp, float humi, int soil, int co2, float water) {
  u8x8.clearDisplay();
  u8x8.setCursor(0, 0);
  u8x8.print("Temp:"); u8x8.print(temp, 1); u8x8.print("C");
  u8x8.setCursor(0, 1);
  u8x8.print("Humi:"); u8x8.print(humi, 1); u8x8.print("%");
  u8x8.setCursor(0, 2);
  u8x8.print("Soil:"); u8x8.print(soil); u8x8.print("%");
  u8x8.setCursor(0, 3);
  u8x8.print("CO2:"); u8x8.print(co2);
  u8x8.setCursor(0, 4);
  u8x8.print("Water:"); u8x8.print(water, 0); u8x8.print("%");
}

// =========================================================
//  打印精简阈值汇总（自动每循环调用）
// =========================================================
void printThresholdSummary() {
  Serial.print(F("阈值汇总: 温度=")); Serial.print(tempLimit,1); Serial.print(F("C"));
  Serial.print(F(" 湿度=")); Serial.print(humiLimit,1); Serial.print(F("%"));
  Serial.print(F(" 土壤=")); Serial.print(soilThreshold); Serial.print(F("%"));
  Serial.print(F(" CO2=")); Serial.print(co2WarningThreshold);
  Serial.print(F(" 水位=")); Serial.print(waterLowThreshold); Serial.print(F("%"));
  Serial.print(F(" 风扇=")); Serial.print(fanManualOverride ? "手动" : "自动");
  Serial.print(F(" 水泵=")); Serial.print(pumpManual ? "手动" : "自动");
  Serial.print(F(" 舵机=")); Serial.print(servoAutoMode ? "自动" : "手动");
  Serial.print(F(" 火焰="));
  if (flameBeepMode == BEEP_AUTO) Serial.print("自动");
  else if (flameBeepMode == BEEP_ON) Serial.print("开启");
  else Serial.print("关闭");
  Serial.print(F(" 人体="));
  if (humanBeepMode == BEEP_AUTO) Serial.print("自动");
  else if (humanBeepMode == BEEP_ON) Serial.print("开启");
  else Serial.print("关闭");
  Serial.println();
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

  // 舵机复位
  myServo.attach(SERVO_PIN);
  myServo.write(0);
  lastServoAngle = 0;
  Serial.println(F("舵机已复位到 0°"));

  u8x8.begin();
  u8x8.setPowerSave(0);
  u8x8.setFont(u8x8_font_chroma48medium8_r);
  u8x8.clearDisplay();
  u8x8.setCursor(0, 0);
  u8x8.print("Hello, OLED!");
  u8x8.setCursor(0, 1);
  u8x8.print("Init OK");
  delay(500);
  u8x8.clearDisplay();

  Serial.println(F("OLED 初始化完成"));

  // 指令清单
  Serial.println(F("=== 指令清单 ==="));
  Serial.println(F("风扇: FAN_ON FAN_OFF FAN_AUTO | GET_TEMP SET_TEMP xx"));
  Serial.println(F("水泵: 1 / 0 / auto"));
  Serial.println(F("CO2: GET_CO2 SET_CO2 xx"));
  Serial.println(F("火焰蜂鸣：FLAME_ON  FLAME_OFF  FLAME_AUTO"));
  Serial.println(F("人体蜂鸣：HUMAN_ON  HUMAN_OFF  HUMAN_AUTO"));
  Serial.println(F("水位指令：GET_WATER  SET_WATER 数值"));
  Serial.println(F("土壤阈值：GET_SOIL   SET_SOIL 数值"));
  Serial.println(F("空气湿度：GET_HUMI   SET_HUMI 数值"));
  Serial.println(F("舵机模式：SERVO_AUTO（自动CO₂控制） SERVO_0 SERVO_90 SERVO_180 SERVO_角度值"));
  Serial.println(F("提示：阈值汇总将在每秒自动打印"));
  Serial.println();

  // 首次打印阈值汇总
  printThresholdSummary();
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
    String raw = Serial.readStringUntil('\n');
    raw.trim();
    Serial.print(F("收到指令: '")); Serial.print(raw); Serial.println(F("'"));

    // ----- 风扇 -----
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
    // ----- 温度阈值 -----
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
    // ----- CO2阈值 -----
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
    // ----- 水泵 -----
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
    // ----- 火焰蜂鸣 -----
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
    // ----- 人体蜂鸣 -----
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
    // ----- 水位阈值 -----
    else if (raw == "GET_WATER") {
      Serial.print(F("-> 当前水位报警下限阈值："));
      Serial.print(waterLowThreshold); Serial.println(F(" %"));
    }
    else if (raw.startsWith("SET_WATER ")) {
      String valStr = raw.substring(10);
      valStr.trim();
      int newWaterTh = valStr.toInt();
      if(newWaterTh >= 0 && newWaterTh <= 100) {
        waterLowThreshold = newWaterTh;
        Serial.print(F("-> 水位下限阈值设置为："));
        Serial.print(waterLowThreshold); Serial.println(F(" %"));
      } else {
        Serial.println(F("-> 水位阈值合法范围：0~100"));
      }
    }
    // ----- 土壤阈值 -----
    else if (raw == "GET_SOIL") {
      Serial.print(F("-> 当前土壤自动浇水阈值："));
      Serial.print(soilThreshold); Serial.println(F(" %"));
    }
    else if (raw.startsWith("SET_SOIL ")) {
      String valStr = raw.substring(9);
      valStr.trim();
      int newSoilTh = valStr.toInt();
      if(newSoilTh >= 0 && newSoilTh <= 100) {
        soilThreshold = newSoilTh;
        Serial.print(F("-> 土壤浇水阈值修改为："));
        Serial.print(soilThreshold); Serial.println(F(" %"));
      } else {
        Serial.println(F("-> 土壤阈值合法范围：0~100"));
      }
    }
    // ----- 空气湿度阈值 -----
    else if (raw == "GET_HUMI") {
      Serial.print(F("-> 当前空气湿度报警阈值："));
      Serial.print(humiLimit); Serial.println(F(" %"));
    }
    else if (raw.startsWith("SET_HUMI ")) {
      String valStr = raw.substring(9);
      valStr.trim();
      float newHumiTh = valStr.toFloat();
      if(newHumiTh > 0 && newHumiTh < 100) {
        humiLimit = newHumiTh;
        Serial.print(F("-> 空气湿度阈值设置为："));
        Serial.print(humiLimit); Serial.println(F(" %"));
      } else {
        Serial.println(F("-> 空气湿度合法范围：0~100"));
      }
    }
    // ========== 舵机控制 ==========
    else if (raw == "SERVO_AUTO") {
      servoAutoMode = true;
      Serial.println(F("-> 舵机自动CO₂控制模式"));
    }
    else if (raw == "SERVO_0") {
      myServo.write(0);
      lastServoAngle = 0;
      Serial.println(F("-> 舵机转到 0°"));
    }
    else if (raw == "SERVO_90") {
      myServo.write(90);
      lastServoAngle = 90;
      Serial.println(F("-> 舵机转到 90°"));
    }
    else if (raw == "SERVO_180") {
      myServo.write(180);
      lastServoAngle = 180;
      Serial.println(F("-> 舵机转到 180°"));
    }
    else if (raw.startsWith("SERVO_")) {
      String valStr = raw.substring(6);
      valStr.trim();
      int angle = valStr.toInt();
      if (angle >= 0 && angle <= 180) {
        myServo.write(angle);
        lastServoAngle = angle;
        Serial.print(F("-> 舵机转到 ")); Serial.print(angle); Serial.println(F("°"));
      } else {
        Serial.println(F("-> 角度范围 0~180"));
      }
    }
    else {
      Serial.print(F("-> 未知指令: ")); Serial.println(raw);
    }
  }

  // ---------- 读取传感器 ----------
  int soilValue = analogRead(SOIL_PIN);
  int soilPercent = map(soilValue, 0, 1023, 0, 100);  // 转百分比
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
  } else {
    waterPercent = 0.0;
  }

  float humidity = dht.readHumidity();
  float temp = dht.readTemperature();

  // ---------- 串口打印传感器实时值（第一行，已删除“阈值”字段） ----------
  Serial.print(F("土壤=")); Serial.print(soilPercent); Serial.print(F("%"));
  Serial.print(F(" CO2=")); Serial.print(co2Raw);
  Serial.print(F(" 人体=")); Serial.print(humanVal);
  Serial.print(F(" 火焰=")); Serial.print(flameVal);
  Serial.print(F(" 水位=")); Serial.print(waterPercent,1); Serial.print(F("%"));
  Serial.print(F(" 距离=")); Serial.print(distance,1); Serial.print(F("cm"));
  Serial.print(F(" 温度=")); Serial.print(temp); Serial.print(F("℃ 湿度=")); Serial.print(humidity); Serial.println(F("%"));

  // ---------- 自动打印阈值汇总（第二行） ----------
  printThresholdSummary();

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
  if (distance == -1 || waterPercent < waterLowThreshold) {
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
    digitalWrite(PUMP_RELAY, (soilPercent < soilThreshold) ? HIGH : LOW);
  }

  // ========== 舵机自动控制（CO₂） ==========
  if (servoAutoMode) {
    int targetAngle = (co2Raw > co2WarningThreshold) ? 180 : 0;
    if (targetAngle != lastServoAngle) {
      myServo.write(targetAngle);
      lastServoAngle = targetAngle;
      Serial.print(F("舵机自动调整到 ")); Serial.print(targetAngle); Serial.println(F("° (CO₂控制)"));
    }
  }

  // ---------- 刷新 OLED ----------
  updateDisplay(temp, humidity, soilPercent, co2Raw, waterPercent);

  delay(1000);
}