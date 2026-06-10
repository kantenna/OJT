"""
저울 데이터 파싱 모듈
=====================
저울이 시리얼로 보내는 '한 줄' 문자열에서 무게 숫자만 뽑아낸다.

CAS CK200SC 출력 예시:
    ST,GS,   37.39,kg
    │  │       │    └ 단위(kg)
    │  │       └ 무게 숫자  ← 우리가 ERP에 붙여넣을 값
    │  └ GS=총중량(Gross) / NT=순중량(Net)
    └ ST=안정(Stable) / US=흔들림(Unstable)

이 모듈은 '파싱'만 담당한다(시리얼·화면과 분리).
→ 그래서 tests/test_parser.py 로 하드웨어 없이 단위 테스트가 가능하다.
"""
from __future__ import annotations
import re
from dataclasses import dataclass

# 부호(+/-)가 있을 수도 있는 소수/정수 한 개를 찾는 정규식
_NUMBER_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")
# 단위(kg, g, t, lb) 를 찾는 정규식 (대소문자 무시)
_UNIT_RE = re.compile(r"(kg|g|t|lb)", re.IGNORECASE)
# 'CAS 저울 데이터'만 인정한다 → 맨 앞이 상태코드 ST(안정)/US(흔들림) 여야 함.
# CAS CK200SC는 항상 'ST,...' 또는 'US,...' 로 시작한다.
# (숫자 시작까지 허용하면 '0w..JO' 같은 깨진 데이터의 0을 무게로 오인함)
_VALID_START_RE = re.compile(r"^\s*(ST|US)", re.IGNORECASE)


@dataclass
class WeightData:
    """파싱 결과 한 건"""
    raw: str          # 원본 문자열 (로그/디버깅용)
    weight: float     # 무게 숫자
    unit: str         # 단위 (kg 등)
    stable: bool      # 안정 여부 (ST=True, US=False)
    gross: bool       # 총중량 여부 (GS=True, NT=False)

    @property
    def text(self) -> str:
        """클립보드/화면에 쓸 문자열 (무게 숫자만)."""
        # 37.39 처럼 소수점 포함, 불필요한 0 정리
        s = f"{self.weight:.2f}".rstrip("0").rstrip(".")
        return s


def append_checksum(payload: str) -> str:
    """payload 에 NMEA 방식 체크섬을 붙여 반환: 'PAYLOAD*HH'.
    (보내는 쪽 시뮬레이터들이 공통으로 사용 → 알고리즘 한 곳에서 관리)
    """
    c = 0
    for ch in payload:
        c ^= ord(ch)
    return f"{payload}*{c:02X}"


def verify_checksum(line: str) -> tuple[str, bool]:
    """체크섬이 있으면 검증한다 (NMEA 방식: 'PAYLOAD*HH').
      HH = PAYLOAD 모든 문자의 XOR 값을 2자리 16진수로.

    반환: (검증할 본문(payload), 통과여부)
      - 체크섬 없음        → (원본, True)   ← 체크섬 안 보내는 저울도 허용(하위호환)
      - 체크섬 있고 일치    → (payload, True)
      - 체크섬 있고 불일치  → (payload, False) ← 전송 중 변조 → 호출측에서 거부
    """
    if "*" not in line:
        return line, True
    payload, _, tail = line.rpartition("*")
    tail = tail.strip()
    # '*' 뒤가 16진수 2자리가 아니면 체크섬으로 보지 않음 (그냥 통과)
    if len(tail) < 2 or any(c not in "0123456789abcdefABCDEF" for c in tail[:2]):
        return line, True
    calc = 0
    for ch in payload:
        calc ^= ord(ch)              # 모든 문자를 XOR
    given = int(tail[:2], 16)
    return payload, (calc == given)


def parse_weight(line: str) -> WeightData | None:
    """
    저울 한 줄 문자열 → WeightData.
    파싱 실패(빈 줄, 숫자 없음 등) 시 None 을 돌려준다.

    CAS 외 다른 제조사가 추가돼도 '숫자+단위' 기반이라 대부분 동작한다.
    """
    if not line:
        return None
    line = line.strip()
    if not line:
        return None

    # 체크섬 검증 — 전송 중 한 글자라도 변조되면 체크섬이 안 맞아 거부된다.
    # (체크섬이 없는 데이터는 그대로 통과 → 하위호환)
    line, ok = verify_checksum(line)
    if not ok:
        return None
    line = line.strip()

    # 저울 데이터 형식이 아니면(쓰레기 등) 거부 → 아무 숫자나 무게로 받아들이지 않음
    if not _VALID_START_RE.match(line):
        return None

    upper = line.upper()

    # 1) 안정/흔들림: 보통 맨 앞 2글자 ST/US
    stable = upper[:2] == "ST"

    # 2) 총중량/순중량
    gross = "NT" not in upper  # NT(순중량)가 아니면 총중량으로 간주

    # 3) 무게 숫자 추출 (핵심)
    m = _NUMBER_RE.search(line)
    if not m:
        return None  # 숫자가 없으면 무게 데이터가 아님
    weight = float(m.group())

    # 4) 단위 추출 — 반드시 '무게 숫자 뒤쪽'에서만 찾는다.
    #    (앞에서 찾으면 'GS'의 G 를 단위 g 로 오인식함)
    um = _UNIT_RE.search(line[m.end():])
    unit = um.group(1).lower() if um else "kg"

    return WeightData(raw=line, weight=weight, unit=unit, stable=stable, gross=gross)


# 모듈을 직접 실행하면 간단한 자가 테스트
if __name__ == "__main__":
    samples = [
        "ST,GS,   37.39,kg",
        "US,GS,    0.00,kg",
        "ST,NT,  -12.5,kg",
        "ST,GS,+00037.39kg",
        "쓰레기 데이터",
        "",
    ]
    for s in samples:
        print(f"{s!r:30} -> {parse_weight(s)}")
