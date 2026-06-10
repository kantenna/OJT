"""
가상 저울 시뮬레이터 (시리얼 송신)
==================================
실제 저울 대신 이 스크립트가 'CAS 형식' 데이터를 시리얼 포트로 1초마다 송신한다.

사용 전제: 가상 시리얼 포트 쌍이 필요하다 (예: com0com 으로 COM4 ↔ COM5 연결).
  - 이 스크립트는 한쪽(COM4)으로 송신
  - main.py 는 반대쪽(COM5)에 연결해서 수신
  ※ 한 쌍의 양 끝이므로, 보내는 포트와 받는 포트는 반드시 서로 다른 끝이어야 한다.
    (같은 포트로 송신+수신 불가 → "액세스 거부" 에러)

실행:  python simulator.py COM4     (그러면 main.py 는 COM5 로 연결)
※ 가상 포트 없이 그냥 동작만 보고 싶으면 main.py 의 [데모 연결] 버튼을 쓰면 된다.
"""
import sys
import os
import time
import random
import serial

# src 폴더의 scale_parser 에서 체크섬 생성 함수 재사용 (송신/수신이 같은 알고리즘 공유)
_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
sys.path.insert(0, _SRC)
from scale_parser import append_checksum


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM4"
    baud = int(sys.argv[2]) if len(sys.argv) > 2 else 9600

    print(f"가상 저울 송신 시작: {port} @ {baud}  (Ctrl+C 로 중지)")
    ser = serial.Serial(port, baud, timeout=1)

    weight = 12.34
    try:
        while True:
            weight += random.uniform(-0.5, 0.5)
            weight = max(0.0, weight)
            status = "ST" if random.random() > 0.3 else "US"
            # CAS 형식 본문 + 체크섬:  ST,GS,   37.39,kg*7A
            payload = f"{status},GS,{weight:8.2f},kg"
            line = append_checksum(payload) + "\r\n"
            ser.write(line.encode("ascii"))
            print("송신:", line.strip())
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n중지")
    finally:
        ser.close()


if __name__ == "__main__":
    main()
