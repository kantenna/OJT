"""
db.py — 칭량 실적 저장 (SQLite)

배합 칭량 실적을 파일 1개(records.db)에 SQL로 저장한다. 서버 불필요.
  - batch    : 생산 LOT (배치 단위)
  - weighing : 칭량 실적 (생산LOT ↔ 원재료LOT 을 잇는 핵심 테이블)

DB 접근을 이 파일 한 곳에 가둔다 → 나중에 MES DB(MSSQL 등)로 바꿔도 여기만 교체.
(recipe.py 가 배합비를, db.py 가 실적 저장을 감싼다)

확인 방법:
  - DBeaver → SQLite 연결 → records.db 열기 → weighing 테이블 조회
  - python -c "import sqlite3; [print(r) for r in sqlite3.connect('records.db').execute('select * from weighing')]"

관련 개념: SQLite, 트랜잭션(commit), LOT 추적
"""

import os
import sqlite3
import logging
from datetime import datetime

from common import paths

log = logging.getLogger("db")

# records.db 위치: 소스 실행=프로젝트 루트, 배포(exe)=exe 옆 (recipe/logs 와 동일 기준)
DB_PATH = os.path.join(paths.base_dir(), "records.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS batch (
    batch_no    TEXT PRIMARY KEY,   -- 생산 LOT (예: P-20260611-01)
    product     TEXT,
    status      TEXT,               -- 진행중 / 완료
    updated_at  TEXT
);
CREATE TABLE IF NOT EXISTS weighing (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_no      TEXT NOT NULL,    -- 생산 LOT
    ingredient    TEXT,             -- 원료명
    material_lot  TEXT,             -- 원재료 LOT
    target_kg     REAL,
    net_kg        REAL,             -- 실투입량(순중량)
    diff_kg       REAL,
    verdict       TEXT,             -- 부족 / 양호 / 초과
    forced        INTEGER,          -- 무시저장 여부 (0/1)
    weighed_at    TEXT
);
"""


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _connect():
    """연결을 열고 테이블이 없으면 만든다."""
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(_SCHEMA)
    return conn


def save_weighing(rec):
    """
    칭량 실적 한 건을 weighing 테이블에 INSERT 한다.
    rec: pop_gui._record() 가 만든 dict. 성공 True / 실패 False.
    """
    try:
        conn = _connect()
        try:
            conn.execute(
                """INSERT INTO weighing
                   (batch_no, ingredient, material_lot, target_kg, net_kg, diff_kg, verdict, forced, weighed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (rec["batch_no"], rec["ingredient"], rec["material_lot"],
                 rec["target_kg"], rec["net_kg"], rec["diff_kg"], rec["verdict"],
                 1 if rec["forced"] else 0, _now()),
            )
            conn.commit()
        finally:
            conn.close()   # 잠금 즉시 해제 → DBeaver 등에서 바로 읽힘
        return True
    except sqlite3.Error as e:
        log.error("칭량 실적 저장 실패: %s", e)
        return False


def save_batch(batch_no, product, status):
    """배치(생산 LOT) 상태를 batch 테이블에 기록/갱신(upsert)한다."""
    try:
        conn = _connect()
        try:
            conn.execute(
                """INSERT INTO batch (batch_no, product, status, updated_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(batch_no)
                   DO UPDATE SET status = excluded.status, updated_at = excluded.updated_at""",
                (batch_no, product, status, _now()),
            )
            conn.commit()
        finally:
            conn.close()
        return True
    except sqlite3.Error as e:
        log.error("배치 저장 실패: %s", e)
        return False
