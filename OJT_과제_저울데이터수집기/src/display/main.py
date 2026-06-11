"""
main.py — 프로그램 진입점

GUI 창을 띄운다. 실제 동작(수신/파싱/표시)은 각 부품 파일이 담당한다.
    - serial_reader.py : 시리얼 수신 (스레드)
    - parser.py        : 무게 추출
    - gui.py           : 화면

실행: python src/display/main.py
"""

import os
import sys
import logging
import tkinter as tk

# src 를 모듈 검색 경로에 추가 → python src/display/main.py 로 직접 실행 가능
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from display.gui import ScaleApp
from common.app_logger import setup_logging


def main():
    logfile = setup_logging()           # 로깅 설정 (파일 + 콘솔)
    log = logging.getLogger("main")
    log.info("프로그램 시작 (로그 파일: %s)", logfile)

    root = tk.Tk()          # 빈 창(루트 윈도) 생성
    ScaleApp(root)          # 우리 앱을 그 창에 올림
    root.mainloop()         # 이벤트 루프 시작 (창이 계속 떠 있게 함)

    log.info("프로그램 종료")


if __name__ == "__main__":
    main()
