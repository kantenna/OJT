"""
가상 저울 시뮬레이터 — 칭량 시나리오 (시리얼 송신)
=================================================
실제 배합 칭량처럼 무게를 만들어 시리얼로 송신한다:
  빈 저울(0) → 원료 부음(점점 증가, US 흔들림) → 목표 근처서 안정(ST, 잠시 유지) → 비움 → 반복
제조사(CAS / AND) 형식 선택 가능. 가끔 과충전(초과) 사이클도 섞여 판정 데모가 자연스럽다.

가상 포트 쌍 필요 (예: com0com 으로 COM5 ↔ COM6).
  - 이 스크립트: 한쪽(COM5)으로 송신
  - 앱(main.py): 반대쪽(COM6)에서 수신
  ※ 송신/수신 포트는 서로 달라야 한다(같으면 "액세스 거부").

실행:
    python simulator/simulator.py <포트> [제조사] [목표kg] [보드레이트]
      제조사: CAS(기본) | AND      목표: 기본 50
    예) python simulator/simulator.py COM5 CAS 60     ← 밀가루 목표 60kg (CAS)
        python simulator/simulator.py COM7 AND 12     ← 설탕  목표 12kg (A&D)

관련 개념: 칭량 시나리오(채우기→안정), 제조사별 형식(scale_formats)
"""
import sys
import os
import time
import random
import serial

# src 폴더의 scale_formats 사용 (제조사별 형식 정의를 송신/수신이 공유)
_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
sys.path.insert(0, _SRC)
import scale_formats


def weighing_cycle(target):
    """
    한 번의 칭량 시퀀스 (무게, 안정여부) 를 차례로 만들어낸다 (제너레이터).

    0 에서 시작해 목표 근처까지 차오르고(US), 안착값에서 안정(ST)된 뒤 0으로 비운다.
    안착값은 보통 목표 근처(양호), 가끔 과충전(초과)이라 판정 데모가 다양해진다.
    """
    # 최종 안착값 결정
    if random.random() < 0.25:
        final = target * random.uniform(1.01, 1.04)      # 과충전 → '초과' 판정 데모
    else:
        final = target * random.uniform(0.997, 1.006)    # 목표 근처 → '양호' 판정

    # 1) 채우기 (붓는 중, US 흔들림) — 목표에 가까울수록 천천히 부음
    w = 0.0
    while w < final - 0.05:
        w += max(0.05, (final - w) * random.uniform(0.15, 0.35))
        jitter = random.uniform(-0.1, 0.1)               # 붓는 중 출렁임
        yield max(0.0, round(w + jitter, 2)), False

    # 2) 안정 (손 뗌, ST) — 같은 값을 잠시 유지 (작업자가 [통과] 누를 시간)
    for _ in range(8):
        yield round(final, 2), True

    # 3) 비우기 (다음 칭량 준비)
    yield 0.0, True


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM5"
    maker = sys.argv[2].upper() if len(sys.argv) > 2 else "CAS"
    target = float(sys.argv[3]) if len(sys.argv) > 3 else 50.0
    baud = int(sys.argv[4]) if len(sys.argv) > 4 else 9600

    if maker not in scale_formats.supported():
        print(f"지원하지 않는 제조사: {maker} (지원: {', '.join(scale_formats.supported())})")
        sys.exit(1)

    print(f"가상 저울(칭량 시나리오): {port} @ {baud}  [{maker}]  목표 {target}kg  (Ctrl+C 로 중지)")
    # write_timeout: 받는 쪽(앱)이 닫혀 버퍼가 차도 write 가 영원히 막히지 않게 한다.
    # (없으면 com0com 에서 write 가 블로킹돼 Ctrl+C 도 안 먹음)
    ser = serial.Serial(port, baud, timeout=1, write_timeout=1)
    try:
        while True:                               # 사이클 반복
            for weight, stable in weighing_cycle(target):
                line = scale_formats.build_line(maker, weight, stable) + "\r\n"
                try:
                    ser.write(line.encode("ascii"))
                    mark = "안정" if stable else "붓는중"
                    print(f"송신: {line.strip():24}  [{mark}]")
                except serial.SerialTimeoutException:
                    # 받는 쪽이 없어 버퍼가 참 → 데이터는 버리고 계속 (앱 켜면 자동 재개)
                    print("대기: 수신 측 없음 (앱 켜면 자동 재개, Ctrl+C 로 중지)")
                time.sleep(0.3)
            time.sleep(1.5)                       # 사이클 사이 쉼
    except KeyboardInterrupt:
        print("\n중지")
    finally:
        ser.close()


if __name__ == "__main__":
    main()
