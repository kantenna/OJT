"""
scale_simulator.py — 파이썬 가상 저울 시뮬레이터 (하드웨어 없이 테스트용)

[2단계] 진짜 저울/아두이노 없이, 파이썬만으로 저울 신호를 흉내 낸다.
        아두이노 스케치(arduino_scale_simulator.ino)와 같은 일을 하지만
        C++/하드웨어 대신 파이썬으로, USB 케이블 대신 '가상 시리얼 포트'로 보낸다.

CAS (CK200SC) 형식:   ST,GS,   37.39,kg
  - ST = Stable(안정) / US = Unstable(흔들림)
  - GS = Gross(총중량)
  - 가운데 = 무게 숫자 (오른쪽 정렬, 앞에 공백)
  - kg = 단위

────────────────────────────────────────────────────────────────────
어떻게 내 프로그램과 연결되나? (가상 시리얼 포트)

  [이 시뮬레이터] ──쓰기──> COM5 ╎ COM6 ──읽기──> [src/main.py]
                                  ╎
                       com0com 이 둘을 내부에서 연결

  1) com0com 같은 도구로 가상 포트 쌍(예: COM5↔COM6)을 만든다.
  2) 터미널 A:  python simulator/scale_simulator.py COM5   ← 저울 역할(송신)
  3) 터미널 B:  python src/main.py                          ← 내 프로그램(COM6 수신)
  ※ 한 포트는 한 프로그램만 열 수 있다. 송신/수신이 같은 포트면 충돌.
────────────────────────────────────────────────────────────────────

단독 실행:
    python simulator/scale_simulator.py            (포트 목록만 보여줌)
    python simulator/scale_simulator.py COM5       (그 포트로 송신 시작)

관련 개념: 가상 시리얼 포트(Virtual COM Port), pyserial, 시리얼 송신(write)
"""

import sys
import time
import random

import serial                        # pyserial (설치: pip install pyserial)
from serial.tools import list_ports  # 연결된 COM 포트 목록 조회용


def show_ports():
    """현재 PC에 보이는 COM 포트 목록을 출력한다 (가상 포트 포함)."""
    ports = list_ports.comports()
    if not ports:
        print("사용 가능한 COM 포트가 없습니다.")
        print("→ com0com 등으로 가상 포트 쌍(예: COM5↔COM6)을 먼저 만드세요.")
        return
    print("사용 가능한 COM 포트:")
    for p in ports:
        print(f"  {p.device}  -  {p.description}")


def make_line():
    """
    저울이 보낼 법한 한 줄을 만든다 (아두이노 .ino 와 같은 규칙).

    - 무게: 36.00 ~ 39.99 사이를 랜덤으로 (실제 저울처럼 값이 조금씩 흔들림)
    - 상태: 5번에 1번 꼴로 흔들림(US), 나머지는 안정(ST)
    - 폭 5칸 오른쪽 정렬 → 앞에 공백이 붙는다 (예: "37.39", "  6.20")
    """
    weight = 36.0 + random.randint(0, 399) / 100.0   # 36.00 ~ 39.99
    status = "ST" if random.randint(0, 4) != 0 else "US"
    weight_str = f"{weight:5.2f}"                     # 폭 5, 소수점 2자리
    return f"{status},GS,{weight_str},kg"


def run(port, baudrate=9600, interval=1.0):
    """
    포트를 열고 저울 형식 문자열을 interval(초)마다 계속 송신한다.

    port     : 송신할 가상 포트 (예: "COM5") — 내 프로그램은 반대쪽(COM6)을 읽는다
    baudrate : 통신 속도 (저울과 동일하게 9600)
    interval : 한 줄 보내고 쉬는 시간(초)
    """
    try:
        # with 로 열면 끝날 때(또는 에러 시) 포트가 자동으로 닫힌다.
        with serial.Serial(port, baudrate, timeout=1) as ser:
            print(f"[송신 시작] {port} @ {baudrate}bps  (Ctrl+C 로 종료)")
            while True:
                line = make_line()
                # println 처럼 끝에 \r\n 을 붙인다 → 받는 쪽 readline() 이 줄을 구분.
                ser.write((line + "\r\n").encode("ascii"))
                print(f"  보냄: {line}")
                time.sleep(interval)
    except serial.SerialException as e:
        # 포트가 없거나 다른 프로그램이 점유 중일 때
        print(f"[에러] 포트 '{port}' 를 열 수 없습니다: {e}")
        print("→ 포트 이름이 맞는지, 다른 프로그램이 잡고 있지 않은지 확인하세요.")
    except KeyboardInterrupt:
        print("\n[종료] 사용자가 Ctrl+C 를 눌렀습니다.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        show_ports()
        print("\n사용법: python simulator/scale_simulator.py <포트이름>"
              "   예) python simulator/scale_simulator.py COM5")
        sys.exit(0)

    run(sys.argv[1])
