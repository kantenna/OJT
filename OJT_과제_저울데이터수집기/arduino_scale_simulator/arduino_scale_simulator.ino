/*
 * arduino_scale_simulator.ino — 아두이노 가상 저울 (실물 시리얼 신호 검증용)
 *
 * 하는 일:
 * - 9600bps 로 CAS 저울 형식 문자열을 1초마다 시리얼로 송신한다.
 * - 진짜 저울처럼 무게가 조금씩 변하고, 가끔 "흔들림(US)" 상태도 섞어 보낸다.
 *
 * CAS (CK200SC) 형식:   ST,GS,   37.39,kg
 *   - ST = Stable(안정) / US = Unstable(흔들림)
 *   - GS = Gross(총중량)
 *   - 가운데 = 무게 숫자 (오른쪽 정렬, 앞에 공백)
 *   - kg = 단위
 *
 * 주의: 업로드 후 Arduino IDE 의 [시리얼 모니터]를 반드시 닫아야
 *       내 프로그램(serial_reader.py)이 COM 포트를 열 수 있다.
 */

void setup() {
  Serial.begin(9600);   // 9600bps 로 시리얼 통신 시작
}

void loop() {
  // 36.00 ~ 39.99 사이의 무게를 흉내 (실제 저울처럼 값이 조금씩 바뀜)
  float weight = 36.0 + (random(0, 400) / 100.0);

  // 5번에 1번 꼴로 "흔들림(US)" 상태, 나머지는 "안정(ST)"
  bool stable = (random(0, 5) != 0);
  const char* status = stable ? "ST" : "US";

  // 무게를 소수점 2자리 문자열로 변환 (예: 37.39)
  char weightStr[10];
  dtostrf(weight, 5, 2, weightStr);  // 폭 5, 소수점 2자리 → "37.39"

  // CAS 형식으로 한 줄 조립해서 송신.
  // println 은 끝에 \r\n 을 붙여준다 → 받는 쪽 readline() 이 줄을 구분할 수 있음.
  Serial.print(status);
  Serial.print(",GS,");
  Serial.print(weightStr);
  Serial.println(",kg");

  delay(1000);  // 1초 대기
}
