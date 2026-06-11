"""
scale_formats.py — 제조사별 저울 '출력 형식' 정의 (보내는 쪽이 사용)

저울 제조사마다 한 줄을 만드는 규칙이 다르다. 이 모듈은 그 규칙을 한 곳에
모아두고, 시뮬레이터가 제조사를 골라 같은 무게를 각 형식으로 송신하게 한다.

지원 형식
---------
- CAS  (CK200SC):  "ST,GS,   37.39,kg"  + NMEA 체크섬 (예: ...,kg*7A)
      상태(ST/US), GS(총중량), 무게(폭8 오른쪽 정렬), 단위(kg)
- AND  (A&D 표준):  "ST,+00037.39 kg"    (체크섬 없음)
      상태(ST/US), 부호(+/-), 무게(앞자리 0 채움 폭8), 단위(3칸 오른쪽 정렬)

받는 쪽(scale_parser.parse_weight)은 'ST/US + 숫자 + 단위' 기반이라 두 형식을
모두 범용으로 파싱한다. → 이 모듈은 '보내는 형식'만 담당한다.

관련 개념: 제조사별 형식 분리(확장 지점), 전략 선택
"""

from scale_parser import append_checksum


def _cas(weight, stable, unit="kg"):
    """CAS CK200SC 형식 + NMEA 체크섬."""
    status = "ST" if stable else "US"
    payload = f"{status},GS,{weight:8.2f},{unit}"   # 무게 폭8 오른쪽 정렬 → 앞 공백
    return append_checksum(payload)


def _and(weight, stable, unit="kg"):
    """A&D 표준 형식 (부호 + 앞자리 0 채움, 체크섬 없음)."""
    status = "ST" if stable else "US"
    sign = "+" if weight >= 0 else "-"
    # 무게: 부호 빼고 폭8(예: 00037.39), 단위: 3칸 오른쪽 정렬(예: " kg")
    return f"{status},{sign}{abs(weight):08.2f}{unit:>3}"


# 제조사 코드 → 한 줄 생성 함수
FORMATS = {
    "CAS": _cas,
    "AND": _and,
}


def build_line(maker, weight, stable, unit="kg"):
    """
    제조사 코드(maker)에 맞는 저울 한 줄을 만든다.
    지원하지 않는 제조사면 ValueError.
    """
    key = maker.upper()
    if key not in FORMATS:
        raise ValueError(
            f"지원하지 않는 제조사: {maker} (지원: {', '.join(FORMATS)})"
        )
    return FORMATS[key](weight, stable, unit)


def supported():
    """지원 제조사 코드 목록."""
    return list(FORMATS)


if __name__ == "__main__":
    # 각 제조사 형식 미리보기 (같은 무게를 형식별로)
    for maker in supported():
        print(f"{maker:5} 안정 -> {build_line(maker, 37.39, True)!r}")
        print(f"{maker:5} 음수 -> {build_line(maker, -12.5, False)!r}")
