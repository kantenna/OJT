"""
paths.py — 실행 환경에 맞는 '기준 폴더'를 알려준다

[9단계 배포 대비] config.json 과 logs/ 를 어디서 찾을지 결정한다.

문제: PyInstaller 로 --onefile exe 를 만들면, 실행 시 코드가 임시 폴더
      (Temp 안의 _MEIxxxx 폴더)에 풀려서 돈다. 그래서 __file__ 은 그 임시 폴더를 가리킨다.
      → config.json 을 엉뚱한 곳에서 찾고, logs/ 도 임시 폴더에 생겼다 사라진다.

해결: 배포(frozen) 상태면 __file__ 대신 exe 위치(sys.executable)를 기준으로 삼는다.
      그러면 config.json·logs 가 'exe 와 같은 폴더'에 놓인다.

      소스 실행:  <프로젝트 루트>/  (src 의 한 단계 위)
      배포(exe):  <exe 가 있는 폴더>/

관련 개념: PyInstaller, sys.frozen, sys.executable
"""

import os
import sys


def base_dir():
    """config.json·logs 의 기준이 되는 폴더 경로를 돌려준다."""
    if getattr(sys, "frozen", False):
        # PyInstaller exe 로 실행 중 → exe 가 있는 폴더
        return os.path.dirname(sys.executable)
    # 소스(.py)로 실행 중 → 이 파일(src/paths.py) 기준 한 단계 위 = 프로젝트 루트
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
