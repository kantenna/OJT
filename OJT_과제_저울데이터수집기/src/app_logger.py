"""
app_logger.py — 로깅(기록) 설정 담당

[7단계] 프로그램이 '언제 무슨 일을 했는지'를 파일과 화면에 동시에 남긴다.
        현장 PC에 개발자가 없어도, 로그 파일만 보면 문제를 추적할 수 있다.
        (--windowed exe 로 배포하면 콘솔이 없으니, 파일 기록이 유일한 단서가 된다)

이 모듈은 setup_logging() 을 프로그램 시작 시 '한 번만' 호출하면 된다.
이후 각 파일에서는 logging.getLogger("이름") 으로 기록만 하면
파일(logs/scale_날짜.log)과 콘솔 양쪽으로 자동 출력된다.

관련 개념: logging 모듈, 핸들러(handler), 로그 레벨(INFO/WARNING/ERROR)
"""

import os
import logging
from datetime import datetime

# 로그 폴더: 이 파일(src/app_logger.py) 기준 한 단계 위의 logs/
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(_ROOT, "logs")


def setup_logging(level=logging.INFO):
    """
    로깅을 설정한다 (파일 + 콘솔 동시 출력). 프로그램 시작 시 한 번만 호출.

    - 파일:   logs/scale_2026-06-10.log  (날짜별로 분리되어 쌓임)
    - 콘솔:   개발 중 터미널에서도 같은 내용을 볼 수 있음
    돌려주는 값: 만들어진 로그 파일 경로 (시작 메시지에 표시용)
    """
    os.makedirs(LOG_DIR, exist_ok=True)  # logs/ 폴더 없으면 생성
    logfile = os.path.join(LOG_DIR, f"scale_{datetime.now():%Y-%m-%d}.log")

    # 형식:  14:32:07 INFO    [serial] COM4 포트 열림 (9600bps)
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)-7s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(level)

    # 이미 설정돼 있으면(중복 호출) 핸들러를 다시 붙이지 않는다 → 로그 중복 방지
    if root.handlers:
        return logfile

    # 파일 핸들러 — 영구 저장 (UTF-8 로 한글 깨짐 방지)
    file_handler = logging.FileHandler(logfile, encoding="utf-8")
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    # 콘솔 핸들러 — 개발 중 터미널 출력용
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)
    root.addHandler(console_handler)

    return logfile
