"""
pop_main.py — 배합 칭량 POP 진입점

레시피(recipe.json)를 읽어 배합 칭량 화면을 띄운다.
기존 단순 무게표시기(main.py)와 별개의 모드.

실행: python src/pop_main.py
"""

import logging
import tkinter as tk

from app_logger import setup_logging
import recipe as recipe_mod
from pop_gui import WeighingPOP


def main():
    logfile = setup_logging()
    log = logging.getLogger("pop_main")
    log.info("배합 칭량 POP 시작 (로그 파일: %s)", logfile)

    rcp = recipe_mod.load_recipe()

    root = tk.Tk()
    if rcp is None:
        root.title("배합 칭량 POP")
        tk.Label(root, text="배합비(recipe.json)를 불러올 수 없습니다.",
                 fg="red", padx=20, pady=20).pack()
        log.error("배합비 로드 실패 — 화면을 띄울 수 없음")
    else:
        WeighingPOP(root, rcp)

    root.mainloop()
    log.info("배합 칭량 POP 종료")


if __name__ == "__main__":
    main()
