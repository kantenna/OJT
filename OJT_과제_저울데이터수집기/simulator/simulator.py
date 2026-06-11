"""
가상 저울 시뮬레이터 — 칭량 시나리오 (시리얼 송신)
=================================================
실제 배합 칭량처럼 무게를 만들어 시리얼로 송신한다:
  빈 저울(0) → 원료 부음(점점 증가, US 흔들림) → 목표 근처서 안정(ST) → 그 값을 '유지'
제조사(CAS / AND) 형식 선택 가능. 가끔 과충전(초과) 칭량도 섞여 판정 데모가 자연스럽다.

실제 저울처럼 '유지'한다 = 자동으로 0으로 떨어지지 않는다.
  → 그럼 언제 비우나? 받는 쪽(앱)이 이 포트를 더 이상 읽지 않으면(=작업자가 통과 후
    다음 원료로 이동) "저울을 비운 것"으로 간주해 0으로 리셋하고 다음 칭량을 준비한다.
  (시뮬레이터는 앱과 별개라 '통과 버튼'을 직접 못 안다. '수신 측 유무'가 유일한 신호다.)

가상 포트 쌍 필요 (예: com0com 으로 COM5 ↔ COM6).
  - 이 스크립트: 한쪽(COM5)으로 송신 / 앱(pop_main.py): 반대쪽(COM6)에서 수신

실행:
    python simulator/simulator.py <포트> [제조사] [목표kg] [보드레이트]
      제조사: CAS(기본) | AND      목표: 기본 50
    예) python simulator/simulator.py COM5 CAS 10     ← 원료1 목표 10kg (CAS)
        python simulator/simulator.py COM7 AND 0.7    ← 원료2 목표 0.7kg (A&D)
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

# 연속 송신 실패가 이만큼이면 '수신 측 없음 = 저울 비움(통과 후 이동)'으로 보고 리셋
GONE_LIMIT = 3


def pick_final(target):
    """이번 칭량의 최종 안착값. 보통 목표 근처(양호), 가끔 과충전(초과)."""
    if random.random() < 0.25:
        return round(target * random.uniform(1.01, 1.04), 2)   # 과충전 → 초과
    return round(target * random.uniform(0.997, 1.006), 2)     # 목표 근처 → 양호


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM5"
    maker = sys.argv[2].upper() if len(sys.argv) > 2 else "CAS"
    target = float(sys.argv[3]) if len(sys.argv) > 3 else 50.0
    baud = int(sys.argv[4]) if len(sys.argv) > 4 else 9600

    if maker not in scale_formats.supported():
        print(f"지원하지 않는 제조사: {maker} (지원: {', '.join(scale_formats.supported())})")
        sys.exit(1)

    print(f"가상 저울(유지 모드): {port} @ {baud}  [{maker}]  목표 {target}kg  (Ctrl+C 로 중지)")
    # write_timeout: 받는 쪽이 없을 때 write 가 영원히 막히지 않게 한다.
    ser = serial.Serial(port, baud, timeout=1, write_timeout=1)

    def send(weight, stable, tag):
        """한 줄 송신. 수신 측 있으면 True, 없으면(타임아웃) False."""
        line = scale_formats.build_line(maker, weight, stable) + "\r\n"
        try:
            ser.write(line.encode("ascii"))
            print(f"송신: {line.strip():24}  [{tag}]")
            return True
        except serial.SerialTimeoutException:
            return False

    try:
        while True:                         # 한 번의 칭량(0 → 목표 → 유지 → 비움)
            final = pick_final(target)
            w = 0.0
            gone = 0
            reset = False

            # 1) 채우기 (붓는 중, US 흔들림)
            while w < final - 0.05:
                w += max(0.05, (final - w) * random.uniform(0.15, 0.35))
                shown = max(0.0, round(w + random.uniform(-0.1, 0.1), 2))
                if send(shown, False, "붓는중"):
                    gone = 0
                else:
                    gone += 1
                    if gone >= GONE_LIMIT:   # 채우는 중 앱이 사라지면 처음부터
                        reset = True
                        break
                time.sleep(0.3)
            if reset:
                continue

            # 2) 안정값 유지 (작업자가 통과 누를 때까지 = 앱이 이 포트를 읽는 동안)
            while True:
                if send(final, True, "안정·유지"):
                    gone = 0
                else:
                    gone += 1
                    if gone >= GONE_LIMIT:   # 앱이 떠남 = 통과 후 비움 → 0 리셋
                        print("비움(0) — 다음 칭량 대기")
                        break
                time.sleep(0.3)
    except KeyboardInterrupt:
        print("\n중지")
    finally:
        ser.close()


if __name__ == "__main__":
    main()
