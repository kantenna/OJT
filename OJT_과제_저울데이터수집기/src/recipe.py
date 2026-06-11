"""
recipe.py — 배합비(레시피) 로더

배합비 = "이 제품을 만들려면 어떤 원료를 각각 몇 kg(±허용오차) 넣어야 하나".
지금은 recipe.json 파일에서 읽지만, 실무에선 MES/ERP DB 에 있다.

설계 포인트: '어디서 읽느냐'를 load_recipe() 한 곳에 가둔다.
  → 나중에 DB(SQLite/SQL)로 바꿔도 이 함수 내부만 고치면 화면 코드는 그대로.
  (config_manager 가 설정을 감싸듯, recipe 가 배합비를 감싼다)

관련 개념: 배합비/BOM, 데이터 접근 분리, dataclass
"""

import os
import json
import logging
from dataclasses import dataclass

import paths   # 실행 환경(소스/배포)에 맞는 기준 폴더

log = logging.getLogger("recipe")

RECIPE_PATH = os.path.join(paths.base_dir(), "recipe.json")


@dataclass
class Ingredient:
    """배합비의 원료 한 줄 (어떤 저울로 얼마를 달지)."""
    name: str            # 원료명 (예: 밀가루)
    spec: str = ""       # 규격 (예: 박력분)
    target_kg: float = 0.0      # 목표중량
    tolerance_kg: float = 0.0   # 허용오차 (±)
    port: str = ""       # 이 원료를 다는 저울의 수신 포트 (예: COM6)
    maker: str = "CAS"   # 저울 제조사 형식 (CAS/AND)
    tare_kg: float = 0.0 # 용기중량 (순중량 계산에 차감)


@dataclass
class Recipe:
    """제품 하나의 배합비."""
    product: str             # 제품명
    batch_no: str            # 배치(생산 LOT) 번호
    ingredients: list        # Ingredient 목록 (투입 순서)


def load_recipe(path=RECIPE_PATH):
    """
    배합비 JSON 을 읽어 Recipe 로 돌려준다.
    파일이 없거나 깨졌으면 None 을 돌려준다(호출측에서 '레시피 없음' 처리).

    ── 나중에 DB로 바꾸려면 이 함수 내부만 SQL 조회로 교체하면 된다. ──
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError) as e:
        log.error("배합비를 읽을 수 없습니다 (%s): %s", path, e)
        return None

    ingredients = [
        Ingredient(
            name=ing.get("name", ""),
            spec=ing.get("spec", ""),
            target_kg=float(ing.get("target_kg", 0.0)),
            tolerance_kg=float(ing.get("tolerance_kg", 0.0)),
            port=ing.get("port", ""),
            maker=ing.get("maker", "CAS"),
            tare_kg=float(ing.get("tare_kg", 0.0)),
        )
        for ing in data.get("ingredients", [])
    ]

    return Recipe(
        product=data.get("product", ""),
        batch_no=data.get("batch_no", ""),
        ingredients=ingredients,
    )


if __name__ == "__main__":
    r = load_recipe()
    if r is None:
        print("배합비를 불러오지 못했습니다.")
    else:
        print(f"제품: {r.product}  (배치 {r.batch_no})")
        for i, ing in enumerate(r.ingredients, 1):
            print(f"  {i}. {ing.name}({ing.spec})  목표 {ing.target_kg}±{ing.tolerance_kg}kg"
                  f"  저울 {ing.port}[{ing.maker}]  용기 {ing.tare_kg}kg")
