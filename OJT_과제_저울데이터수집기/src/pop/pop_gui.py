"""
pop_gui.py — 배합 칭량 POP 화면 (Tkinter)

식품 MES의 '계량 입력' 화면을 본떠, 레시피(recipe.json)대로 원료를 순서대로
달면서 목표±허용오차로 판정한다.

흐름:
  레시피 로드 → 현재 원료의 저울(포트) 수신 → 무게 실시간 표시
    → judge 로 부족/양호/초과 판정(신호등 색) → 안정+양호면 [통과] 활성
    → 통과/무시저장 → 실적 기록 → 다음 원료 → 모두 끝나면 배치 완료

부품: recipe(배합비) · serial_reader(수신) · scale_parser(파싱) · judge(판정)

관련 개념: POP 단말, 목표±허용 판정, 원료 순차 진행
"""

import queue
import logging
import tkinter as tk
from tkinter import ttk

from common.serial_reader import SerialReader
from common import scale_parser
from pop import judge as judge_mod
from pop import db

log = logging.getLogger("pop")

# 판정별 색 (연한 배경 + 진한 글씨) — 스크린샷의 판정 바 느낌
_COLORS = {
    judge_mod.OK:    ("#d4edda", "#155724"),   # 양호: 초록
    judge_mod.UNDER: ("#fff3cd", "#856404"),   # 부족: 노랑
    judge_mod.OVER:  ("#f8d7da", "#721c24"),   # 초과: 빨강
}


def _next_batch_no(no):
    """배치 LOT 번호의 끝 숫자를 1 증가. 예: P-20260611-01 → P-20260611-02"""
    head, sep, tail = no.rpartition("-")
    if sep and tail.isdigit():
        return f"{head}-{int(tail) + 1:0{len(tail)}d}"
    return f"{no}-2"


class WeighingPOP:
    def __init__(self, root, recipe):
        self.root = root
        self.recipe = recipe
        self.idx = 0                # 현재 원료 인덱스
        self.batch_no = recipe.batch_no   # 현재 배치(생산 LOT) — 배치마다 증가
        self.reader = None
        self.last_judgment = None   # 최근 판정 (통과 처리에 사용)
        self.last_measured = None   # 최근 계량값
        self.results = []           # 이번 배치의 칭량 실적 (원료별, 배치 완료 시 초기화)

        root.title("배합 칭량 POP")
        root.geometry("430x660")

        self._build_ui()
        root.protocol("WM_DELETE_WINDOW", self.on_close)

        self._start_ingredient()    # 첫 원료부터 수신 시작
        self._poll_queue()

    # ── 현재 원료 ──────────────────────────────────────────
    def current(self):
        return self.recipe.ingredients[self.idx]

    # ── 화면 구성 ──────────────────────────────────────────
    def _build_ui(self):
        # 헤더 (파란 띠)
        header = tk.Frame(self.root, bg="#1f6fb2")
        header.pack(fill="x")
        tk.Label(header, text="계량 입력", bg="#1f6fb2", fg="white",
                 font=("맑은 고딕", 15, "bold")).pack(pady=8)

        body = ttk.Frame(self.root, padding=12)
        body.pack(fill="both", expand=True)

        # 상단 정보 행들 (라벨 좌 / 값 우)
        self.row_vals = {}
        for label in ("자재명", "이론사용중량", "제품로트", "진행"):
            row = ttk.Frame(body)
            row.pack(fill="x", pady=2)
            ttk.Label(row, text=label, width=10).pack(side="left")
            v = ttk.Label(row, text="-", font=("맑은 고딕", 11, "bold"))
            v.pack(side="right")
            self.row_vals[label] = v

        # 자재로트 (스캔/입력 + 목록선택)
        lot = ttk.Frame(body)
        lot.pack(fill="x", pady=(8, 2))
        ttk.Label(lot, text="자재로트", width=10).pack(side="left")
        self.lot_entry = ttk.Entry(lot)
        self.lot_entry.pack(side="left", fill="x", expand=True, padx=4)
        ttk.Button(lot, text="목록선택", command=self._pick_lot).pack(side="left")

        ttk.Separator(body).pack(fill="x", pady=8)

        # 계량값 (큰 박스)
        ttk.Label(body, text="계량값 (kg)").pack(anchor="w")
        self.weight_box = tk.Label(body, text="--", font=("Segoe UI", 40, "bold"),
                                   relief="solid", bd=1, fg="#1f6fb2")
        self.weight_box.pack(fill="x", pady=4)

        # 순중량 / 남은 양(미계량)
        self.remain_label = ttk.Label(body, text="", font=("맑은 고딕", 10))
        self.remain_label.pack(anchor="w", pady=2)

        # 판정 바
        self.verdict_bar = tk.Label(body, text="대기 중", font=("맑은 고딕", 12, "bold"),
                                    bg="#e9ecef", fg="#333", pady=8)
        self.verdict_bar.pack(fill="x", pady=8)

        # 버튼 3개
        btns = ttk.Frame(body)
        btns.pack(fill="x", pady=4)
        self.pass_btn = ttk.Button(btns, text="통과", command=self.on_pass, state="disabled")
        self.pass_btn.pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(btns, text="취소", command=self.on_cancel).pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(btns, text="무시저장", command=self.on_force_save).pack(side="left", expand=True, fill="x", padx=2)

        # 다음 배치 버튼 (배치 완료 시에만 활성)
        self.next_btn = ttk.Button(body, text="다음 배치 시작", command=self._next_batch, state="disabled")
        self.next_btn.pack(fill="x", pady=(8, 0))

        self.status = ttk.Label(body, text="", font=("맑은 고딕", 9), foreground="gray")
        self.status.pack(anchor="w", pady=(6, 0))

    # ── 원료 시작/전환 ─────────────────────────────────────
    def _start_ingredient(self):
        """현재 원료의 저울 포트로 수신을 시작하고 화면을 갱신한다."""
        if self.reader:
            self.reader.stop()
            self.reader = None

        ing = self.current()
        self.last_judgment = None
        self.last_measured = None

        # 배치 시작(첫 원료)이면 batch 테이블에 '진행중' 기록
        if self.idx == 0:
            db.save_batch(self.batch_no, self.recipe.product, "진행중")

        # 상단 정보 갱신
        self.row_vals["자재명"].config(text=ing.name)
        self.row_vals["이론사용중량"].config(
            text=f"{ing.target_kg:.2f} ± {ing.tolerance_kg:.2f} kg", foreground="#1f6fb2")
        self.row_vals["제품로트"].config(text=self.batch_no)
        self.row_vals["진행"].config(text=f"{self.idx + 1} / {len(self.recipe.ingredients)}")

        # 입력 초기화
        self.lot_entry.delete(0, "end")

        self.weight_box.config(text="--", fg="#1f6fb2")
        self.remain_label.config(text="")
        self.verdict_bar.config(text="대기 중", bg="#e9ecef", fg="#333")
        self.pass_btn.config(state="disabled")

        # 저울 수신 시작
        self.reader = SerialReader(ing.port, 9600)
        self.reader.start()
        self.status.config(text=f"저울 {ing.port}[{ing.maker}] 수신 중...")
        log.info("원료 칭량 시작: %s (목표 %.2f±%.2f, %s)",
                 ing.name, ing.target_kg, ing.tolerance_kg, ing.port)

    # ── 큐 폴링 ────────────────────────────────────────────
    def _poll_queue(self):
        if self.reader:
            try:
                while True:
                    item = self.reader.queue.get_nowait()
                    if isinstance(item, scale_parser.WeightData):
                        self._update(item)
                    else:  # ("error", 메시지)
                        log.warning("수신 에러: %s", item[1])
                        self.status.config(text=f"에러: {item[1]}")
                        self.reader.stop()
                        self.reader = None
                        break
            except queue.Empty:
                pass
        self.root.after(100, self._poll_queue)

    def _update(self, reading):
        """계량값 수신 → 판정 → 화면 갱신."""
        ing = self.current()
        j = judge_mod.judge(reading.weight, ing.target_kg, ing.tolerance_kg,
                            tare=ing.tare_kg, stable=reading.stable)
        self.last_judgment = j
        self.last_measured = reading.weight

        bg, fg = _COLORS[j.verdict]
        # 계량값 (글씨색은 판정색)
        self.weight_box.config(text=f"{reading.weight:.2f}", fg=fg)
        # 남은 양(미계량)
        remain = max(0.0, ing.target_kg - j.net)
        self.remain_label.config(text=f"순중량 {j.net:.2f} kg   |   미계량 {remain:.2f} kg")
        # 판정 바
        stable_txt = "" if reading.stable else "  (흔들림 — 안정 대기)"
        self.verdict_bar.config(
            text=f"{j.verdict}  차이 {j.diff:+.2f}kg  (오차 {j.error_pct:+.2f}%){stable_txt}",
            bg=bg, fg=fg)
        # 통과 버튼: 안정+양호일 때만
        self.pass_btn.config(state="normal" if j.can_pass else "disabled")

    # ── 버튼 동작 ──────────────────────────────────────────
    def _pick_lot(self):
        """목록선택(데모) — 임시 로트번호를 넣어준다."""
        ing = self.current()
        self.lot_entry.delete(0, "end")
        self.lot_entry.insert(0, f"M-{ing.name}-LOT")

    def _record(self, forced):
        """현재 원료의 칭량 실적을 기록(메모리+로그). CSV 저장은 다음 단계."""
        ing = self.current()
        j = self.last_judgment
        rec = {
            "batch_no": self.batch_no,
            "ingredient": ing.name,
            "material_lot": self.lot_entry.get().strip(),
            "target_kg": ing.target_kg,
            "net_kg": j.net,
            "diff_kg": j.diff,
            "verdict": j.verdict,
            "forced": forced,
        }
        self.results.append(rec)
        db.save_weighing(rec)        # SQLite weighing 테이블에 INSERT
        level = log.warning if forced else log.info
        level("칭량 %s: %s 실투입 %.2fkg [%s]%s",
              "강제저장" if forced else "통과", ing.name, j.net, j.verdict,
              " (범위초과 강제)" if forced else "")

    def on_pass(self):
        """통과 — 안정+양호일 때만 활성. 실적 기록 후 다음 원료."""
        if not (self.last_judgment and self.last_judgment.can_pass):
            return
        self._record(forced=False)
        self._advance()

    def on_force_save(self):
        """무시저장 — 범위를 벗어나도 강제로 기록(로그 경고) 후 다음 원료."""
        if self.last_judgment is None:
            self.status.config(text="아직 계량값이 없습니다.")
            return
        self._record(forced=True)
        self._advance()

    def on_cancel(self):
        """취소 — 현재 원료의 입력(자재로트)을 초기화."""
        self.lot_entry.delete(0, "end")
        self.status.config(text="입력을 취소했습니다.")

    def _advance(self):
        """다음 원료로. 마지막이면 배치 완료."""
        if self.idx + 1 < len(self.recipe.ingredients):
            self.idx += 1
            self._start_ingredient()
        else:
            self._finish()

    def _finish(self):
        """모든 원료 완료 — 수신 중지 + 완료 + 다음 배치 대기."""
        if self.reader:
            self.reader.stop()
            self.reader = None
        self.weight_box.config(text="✓", fg="#155724")
        self.verdict_bar.config(text=f"배치 완료 — {self.batch_no} (원료 {len(self.results)}건)",
                                bg="#d4edda", fg="#155724")
        self.pass_btn.config(state="disabled")
        self.next_btn.config(state="normal")   # 다음 배치 버튼 열기
        self.status.config(text="[다음 배치 시작]을 누르면 새 LOT 으로 이어집니다.")
        db.save_batch(self.batch_no, self.recipe.product, "완료")   # 배치 상태 갱신
        log.info("배치 완료: %s, 원료 %d건", self.batch_no, len(self.results))

    def _next_batch(self):
        """다음 배치(새 생산 LOT)로 — LOT 번호 증가, 처음 원료부터 다시."""
        self.batch_no = _next_batch_no(self.batch_no)
        self.idx = 0
        self.results = []                       # 새 배치의 실적은 새로 모음
        self.next_btn.config(state="disabled")
        log.info("다음 배치 시작: %s", self.batch_no)
        self._start_ingredient()

    def on_close(self):
        if self.reader:
            self.reader.stop()
        self.root.destroy()
