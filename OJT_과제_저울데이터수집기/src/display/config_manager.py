"""
config_manager.py — 설정 파일(config.json) 읽기/쓰기 담당

[7단계] 포트·보드레이트 같은 값을 코드에 박지 않고 config.json 에 저장한다.
        → 현장 PC마다 포트가 달라도 코드를 안 고치고 파일만 바꾸면 된다.
        → 사용자가 GUI에서 고른 포트를 저장해두면 다음 실행 때 기억된다.

설계 포인트 (예외 처리):
- config.json 이 없으면 → 기본값으로 새로 만든다 (죽지 않음).
- config.json 이 깨졌으면(JSON 오류) → 기본값으로 되돌린다 (죽지 않음).
- 일부 키가 빠졌으면 → 기본값으로 채워서 돌려준다.

관련 개념: 설정 파일(JSON), json 모듈, 예외 처리(try/except)
"""

import os
import json
import logging

from common import paths   # 실행 환경(소스/배포)에 맞는 기준 폴더 제공

log = logging.getLogger("config")

# 설정 파일 위치: 소스 실행=프로젝트 루트, 배포(exe)=exe 와 같은 폴더
CONFIG_PATH = os.path.join(paths.base_dir(), "config.json")

# 설정의 기본값. 파일이 없거나 키가 빠지면 이 값으로 채운다.
DEFAULT_CONFIG = {
    "port": "",                    # 마지막으로 쓴 포트 (빈 값이면 자동 선택)
    "baudrate": 9600,              # 통신 속도 (저울과 동일하게)
    "bytesize": 8,
    "parity": "N",
    "stopbits": 1,
    "manufacturer": "CAS",
    "copy_only_when_stable": True,  # 안정(ST)일 때만 클립보드 복사
}


def load_config(path=CONFIG_PATH):
    """
    config.json 을 읽어 dict 로 돌려준다.
    파일이 없거나 깨졌으면 기본값으로 안전하게 복구한다 (예외로 죽지 않음).
    빠진 키는 기본값으로 채운다.
    """
    # 기본값 복사본에서 시작 → 읽은 값으로 덮어쓰기 (빠진 키 자동 보충)
    config = dict(DEFAULT_CONFIG)

    if not os.path.exists(path):
        return config  # 파일이 아직 없음 → 기본값 그대로

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            config.update(data)     # 파일에 있는 값으로 덮어씀
    except (json.JSONDecodeError, OSError) as e:
        # JSON 이 깨졌거나 읽기 실패 → 기본값 유지 (프로그램은 계속 돈다)
        log.warning("config.json 읽기 실패 — 기본값 사용: %s", e)

    return config


def save_config(config, path=CONFIG_PATH):
    """
    dict 를 config.json 에 보기 좋게(들여쓰기) 저장한다.
    저장 실패해도 프로그램이 죽지 않도록 예외를 삼킨다.
    성공하면 True, 실패하면 False 를 돌려준다.
    """
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except OSError as e:
        log.error("config.json 저장 실패: %s", e)
        return False


def update_config(updates, path=CONFIG_PATH):
    """
    기존 설정을 읽어 일부 키만 바꿔 다시 저장하는 편의 함수.
    예) update_config({"port": "COM4"})  → 포트만 갱신해서 저장
    """
    config = load_config(path)
    config.update(updates)
    return save_config(config, path)


if __name__ == "__main__":
    # 단독 테스트: 읽고 → 바꾸고 → 다시 읽어 확인
    print("[현재 설정]")
    cfg = load_config()
    for k, v in cfg.items():
        print(f"  {k} = {v!r}")

    print("\n[테스트] port 를 'COM4' 로 바꿔 저장 후 다시 읽기")
    update_config({"port": "COM4"})
    print(f"  port = {load_config()['port']!r}")
