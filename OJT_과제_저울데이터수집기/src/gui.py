"""
gui.py — Tkinter 화면 담당

[4·5단계] 무게를 크게 보여주는 창. 포트 선택 + 시작/정지 버튼.
수신은 SerialReader(별도 스레드)가 하고, GUI는 after()로 큐를 0.1초마다
들여다보며 화면만 갱신한다. → 창이 얼어붙지 않는다.

관련 개념: Tkinter, 위젯, 이벤트 루프(mainloop), after(), Queue
"""

import queue
import tkinter as tk
from tkinter import ttk

from serial.tools import list_ports

from serial_reader import SerialReader
import parser
import clipboard_util


class ScaleApp:
    def __init__(self, root):
        self.root = root
        self.reader = None       # 시작 버튼을 누르면 SerialReader 객체가 들어간다
        self.last_copied = None  # 같은 무게를 매번 다시 복사하지 않도록 마지막 복사값 기억

        root.title("저울 데이터 수집기")
        root.geometry("360x340")

        # --- 포트 선택 줄 ---
        top = ttk.Frame(root, padding=10)
        top.pack(fill="x")
        ttk.Label(top, text="포트:").pack(side="left")
        self.port_box = ttk.Combobox(top, width=12, state="readonly")
        self.port_box.pack(side="left", padx=5)
        ttk.Button(top, text="새로고침", command=self.refresh_ports).pack(side="left")

        # --- 무게 표시 (크게) ---
        self.weight_label = ttk.Label(root, text="-- kg", font=("Segoe UI", 40, "bold"))
        self.weight_label.pack(pady=10)

        # --- 상태 표시 (안정/흔들림) ---
        self.status_label = ttk.Label(root, text="대기 중", font=("Segoe UI", 12))
        self.status_label.pack()

        # --- 자동복사 켜기/끄기 + 복사 안내 ---
        self.autocopy_var = tk.BooleanVar(value=True)  # 기본 켜짐
        ttk.Checkbutton(root, text="안정될 때 자동 복사", variable=self.autocopy_var).pack(pady=2)
        self.copy_label = ttk.Label(root, text="", font=("Segoe UI", 10), foreground="blue")
        self.copy_label.pack()

        # --- 시작/정지 버튼 ---
        btns = ttk.Frame(root, padding=10)
        btns.pack()
        self.start_btn = ttk.Button(btns, text="시작", command=self.start)
        self.start_btn.pack(side="left", padx=5)
        self.stop_btn = ttk.Button(btns, text="정지", command=self.stop, state="disabled")
        self.stop_btn.pack(side="left", padx=5)

        self.refresh_ports()

        # 창이 닫힐 때 스레드도 깨끗이 정리되도록 연결
        root.protocol("WM_DELETE_WINDOW", self.on_close)

        # 큐 들여다보기 시작 (0.1초마다 반복)
        self._poll_queue()

    def refresh_ports(self):
        """연결된 COM 포트 목록을 콤보박스에 채운다."""
        ports = [p.device for p in list_ports.comports()]
        self.port_box["values"] = ports
        if ports and not self.port_box.get():
            self.port_box.current(0)  # 첫 번째 포트를 기본 선택

    def start(self):
        """시작 버튼: 선택한 포트로 수신 스레드를 띄운다."""
        port = self.port_box.get()
        if not port:
            self.status_label.config(text="포트를 선택하세요", foreground="red")
            return
        self.last_copied = None  # 새로 시작하면 복사 기록 초기화
        self.reader = SerialReader(port, 9600)
        self.reader.start()
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.status_label.config(text=f"{port} 수신 중...", foreground="black")

    def stop(self):
        """정지 버튼: 수신 스레드를 멈춘다."""
        if self.reader:
            self.reader.stop()
            self.reader = None
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.status_label.config(text="정지됨", foreground="black")

    def _poll_queue(self):
        """
        [GUI 스레드] 큐에 쌓인 결과를 모두 꺼내 화면을 갱신한다.
        readline() 처럼 멈추지 않고, '있으면 꺼내고 없으면 넘어간다'(get_nowait).
        """
        if self.reader:
            try:
                while True:  # 큐가 빌 때까지 한 번에 비운다 (최신 값으로 갱신)
                    item = self.reader.queue.get_nowait()
                    if isinstance(item, parser.ScaleReading):
                        self._update_display(item)
                    else:  # ("error", 메시지)
                        self.status_label.config(text=f"에러: {item[1]}", foreground="red")
                        self.stop()
            except queue.Empty:
                pass  # 큐가 비면 그냥 넘어간다 (멈추지 않음!)

        # 0.1초 뒤에 자기 자신을 다시 호출 → 주기적으로 큐 확인
        self.root.after(100, self._poll_queue)

    def _update_display(self, reading):
        """무게/상태 라벨을 갱신하고, 안정 상태면 자동 복사한다."""
        self.weight_label.config(text=f"{reading.weight} {reading.unit}")
        if reading.stable:
            self.status_label.config(text="● 안정", foreground="green")
            self._maybe_copy(reading.weight)
        else:
            self.status_label.config(text="● 흔들림", foreground="orange")

    def _maybe_copy(self, weight):
        """
        안정 상태일 때 무게를 클립보드에 복사한다.
        단, 자동복사가 켜져 있고 + 직전과 값이 다를 때만 (같은 값 반복 복사 방지).
        """
        if not self.autocopy_var.get():
            return
        if weight == self.last_copied:
            return  # 이미 복사한 값과 같으면 건너뜀
        text = str(weight)
        clipboard_util.copy_to_clipboard(self.root, text)
        self.last_copied = weight
        self.copy_label.config(text=f"복사됨: {text}  (ERP에서 Ctrl+V)")

    def on_close(self):
        """창을 닫을 때 수신 스레드 정리 후 종료."""
        if self.reader:
            self.reader.stop()
        self.root.destroy()
