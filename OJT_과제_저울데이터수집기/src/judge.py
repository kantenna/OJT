"""
judge.py — 칭량 판정 로직 (목표 ± 허용오차)

배합 칭량에서 "지금 무게가 목표에 맞나?"를 계산한다. 화면과 분리된 순수 함수라
하드웨어/GUI 없이 단위 테스트가 가능하다.

계산 절차 (식품 MES 계량 화면과 동일)
  순중량 = 계량값 − 용기중량(tare)
  차이   = 순중량 − 목표
  오차%  = 차이 / 목표 × 100
  판정   = 부족(차이<−허용) / 양호(|차이|≤허용) / 초과(차이>+허용)
  통과가능 = 안정(ST) AND 양호      ← '통과' 버튼이 열리는 조건

관련 개념: 목표±허용오차, 순중량(tare 차감), 안정 게이트
"""

from dataclasses import dataclass

# 판정 결과 코드
UNDER = "부족"
OK = "양호"
OVER = "초과"


@dataclass
class Judgment:
    """판정 결과 한 건."""
    net: float         # 순중량 = 계량값 − 용기중량
    diff: float        # 차이 = 순중량 − 목표 (양수=많음, 음수=적음)
    error_pct: float   # 오차% = 차이 / 목표 × 100
    verdict: str       # 부족 / 양호 / 초과
    can_pass: bool     # 안정 AND 양호일 때만 True ('통과' 버튼 활성)

    @property
    def color(self):
        """화면 신호등 색."""
        return "green" if self.verdict == OK else "red"

    @property
    def message(self):
        """작업자에게 보여줄 안내 문구."""
        if self.verdict == OK:
            return "양호 — 통과 가능"
        if self.verdict == UNDER:
            return f"부족 — {abs(self.diff):.2f}kg 더 넣으세요"
        return f"초과 — {abs(self.diff):.2f}kg 덜어내세요"


def judge(measured, target, tolerance, tare=0.0, stable=False):
    """
    계량값을 목표±허용오차로 판정한다.

    measured  : 저울이 읽은 값(계량값)
    target    : 목표중량
    tolerance : 허용오차(±)
    tare      : 용기중량(빼야 순중량)
    stable    : 안정(ST) 여부 — 통과 가능 판단에 사용
    """
    net = measured - tare
    diff = net - target
    error_pct = (diff / target * 100) if target else 0.0

    if diff < -tolerance:
        verdict = UNDER
    elif diff > tolerance:
        verdict = OVER
    else:
        verdict = OK

    can_pass = stable and verdict == OK

    return Judgment(
        net=round(net, 4),
        diff=round(diff, 4),
        error_pct=round(error_pct, 2),
        verdict=verdict,
        can_pass=can_pass,
    )


if __name__ == "__main__":
    # 목표 60kg, 허용 ±0.5kg 기준 몇 가지 상황
    print("목표 60.0kg, 허용 ±0.5kg")
    cases = [
        ("붓는 중 45", 45.0, False),
        ("거의 다 59.7", 59.7, False),
        ("안정 60.02", 60.02, True),
        ("안정인데 부족 59.0", 59.0, True),
        ("안정인데 초과 61.2", 61.2, True),
    ]
    for label, measured, stable in cases:
        j = judge(measured, target=60.0, tolerance=0.5, stable=stable)
        print(f"  {label:16} → 순{j.net:6.2f} 차이{j.diff:+6.2f} "
              f"({j.error_pct:+6.2f}%)  [{j.verdict}] 통과={j.can_pass}  | {j.message}")
