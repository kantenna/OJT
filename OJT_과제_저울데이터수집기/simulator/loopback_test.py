"""
loopback_test.py — 하드웨어 없이 시리얼 파이프라인 검증 (com0com 도 불필요)

[2단계 보조] 가상 포트 도구(com0com)를 설치하기 전에도, 시뮬레이터가 만든 줄이
            '시리얼로 써서 → 시리얼로 다시 읽어 → 파서로 무게 추출'까지
            제대로 도는지 한 프로세스 안에서 검증한다.

비결: pyserial 의 내장 루프백 포트 'loop://'.
  - serial.serial_for_url("loop://") 로 열면, write() 한 바이트가 곧바로
    같은 핸들의 read() 로 돌아온다. (실제 COM 포트/케이블/드라이버 없음)
  - 즉 "송신 → 수신" 을 케이블 없이 흉내 낼 수 있다.

  [시뮬레이터 make_line()] → ser.write() ─loop://─> ser.readline() → parser.parse_line()

실행:
    python simulator/loopback_test.py

※ 이건 '자동 검증용'이다. 두 프로그램(시뮬레이터 ↔ 내 GUI)을 따로 띄워
  테스트하려면 com0com 같은 진짜 가상 포트 쌍이 필요하다 (README 참고).
"""

import os
import sys

import serial  # pyserial

# 같은 폴더의 scale_simulator + src 폴더의 parser 를 불러오기 위한 경로 추가
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

import scale_simulator as sim
import parser


def main(count=10):
    # loop:// : 쓴 데이터가 그대로 다시 읽히는 가상 포트 (하드웨어 불필요)
    ser = serial.serial_for_url("loop://", baudrate=9600, timeout=1)

    ok = 0
    print(f"[루프백 테스트] {count}줄을 시리얼로 써서 다시 읽고 파싱합니다.\n")
    for i in range(count):
        line = sim.make_line()                       # 시뮬레이터가 한 줄 생성
        ser.write((line + "\r\n").encode("ascii"))   # 시리얼로 송신 (loop:// 로 되돌아옴)

        raw = ser.readline()                         # 같은 포트에서 한 줄 수신
        received = raw.decode("ascii", errors="replace").strip()
        reading = parser.parse_line(received)        # 무게 추출

        passed = reading is not None and received == line
        ok += 1 if passed else 0
        mark = "OK " if passed else "FAIL"
        status = ("안정" if reading.stable else "흔들림") if reading else "-"
        weight = f"{reading.weight} {reading.unit}" if reading else "(파싱 실패)"
        print(f"  [{mark}] 보냄 {line!r:22} → 받음 {received!r:22} → {weight} [{status}]")

    ser.close()
    print(f"\n결과: {ok}/{count} 통과")
    return 0 if ok == count else 1


if __name__ == "__main__":
    sys.exit(main())
