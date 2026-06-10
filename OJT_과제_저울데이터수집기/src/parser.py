"""
parser.py — 저울 데이터 파싱 담당

[3단계] 받은 한 줄에서 무게 숫자와 안정/불안정 상태를 뽑아낸다.

지원 형식:
- CAS (CK200SC):  "ST,GS,36.29,kg"
    상태(ST/US) , GS , 무게 , 단위

이 파일은 단독 실행해서 테스트할 수 있다 (아두이노 없이도 OK):
    python src/parser.py

관련 개념: 문자열 파싱, 정규식(re 모듈), dataclass
"""

import re
from dataclasses import dataclass

# 무게 숫자를 찾는 정규식.
#   -?      : 마이너스 부호가 있을 수도 (음수 무게)
#   \d+     : 숫자 1개 이상 (정수 부분)
#   (\.\d+)?: 소수점 + 숫자 (소수 부분, 있을 수도 없을 수도)
WEIGHT_PATTERN = re.compile(r"-?\d+(\.\d+)?")


@dataclass
class ScaleReading:
    """파싱 결과를 담는 그릇."""
    weight: float    # 무게 숫자 (예: 36.29)
    stable: bool     # True=안정(ST), False=흔들림(US)
    unit: str        # 단위 (예: "kg")
    raw: str         # 원본 줄 (디버깅용)


def parse_line(line: str):
    """
    한 줄을 파싱해서 ScaleReading 을 돌려준다.
    무게를 못 찾으면 None 을 돌려준다. (빈 줄, 깨진 줄 등)
    """
    if not line:
        return None

    # 콤마로 자르고 앞뒤 공백 제거 → ["ST", "GS", "36.29", "kg"]
    parts = [p.strip() for p in line.split(",")]

    # 상태 판단: 첫 칸이 "ST" 면 안정, 그 외(US 등)는 불안정으로 본다.
    stable = parts[0].upper() == "ST" if parts else False

    # 단위: 마지막 칸을 단위로 본다 (예: "kg"). 없으면 빈 문자열.
    unit = parts[-1] if len(parts) >= 2 else ""

    # 무게: 줄 전체에서 첫 번째로 나오는 숫자를 무게로 뽑는다.
    match = WEIGHT_PATTERN.search(line)
    if match is None:
        return None  # 숫자가 아예 없으면 파싱 실패

    weight = float(match.group())  # 문자열 "36.29" → 숫자 36.29

    return ScaleReading(weight=weight, stable=stable, unit=unit, raw=line)


if __name__ == "__main__":
    # 아두이노 없이 파싱 로직만 테스트한다.
    samples = [
        "ST,GS,36.29,kg",      # 정상 (안정)
        "US,GS,38.10,kg",      # 흔들림
        "ST,GS,   37.39,kg",   # 공백이 섞인 경우
        "ST,GS,-1.50,kg",      # 음수
        "",                    # 빈 줄 → None 이어야 함
        "garbage line",        # 숫자 없는 줄 → None 이어야 함
    ]
    for s in samples:
        result = parse_line(s)
        print(f"입력: {s!r:25}  →  {result}")
