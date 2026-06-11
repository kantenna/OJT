"""
clipboard_util.py — 클립보드 복사 담당 (이 과제의 핵심 기능)

추출한 무게 값을 클립보드에 복사한다.
작업자는 ERP/메모장에서 Ctrl+V 로 붙여넣는다.

여기서는 별도 설치 없이 'Tkinter 내장 클립보드'를 쓴다.
(원하면 pyperclip 으로 바꿔도 됨 — 아래 NOTE 참고)

관련 개념: 클립보드, Tkinter clipboard_clear/clipboard_append
"""


def copy_to_clipboard(widget, text: str):
    """
    Tkinter 위젯을 통해 text 를 시스템 클립보드에 복사한다.

    widget : 아무 Tkinter 위젯이나 OK (보통 root 창을 넘김)
    text   : 복사할 문자열 (예: "36.29")
    """
    widget.clipboard_clear()      # 기존 클립보드 내용 비우기
    widget.clipboard_append(text) # 새 내용 넣기
    widget.update()               # 즉시 시스템에 반영


# NOTE: pyperclip 으로 바꾸고 싶다면 (pip install pyperclip 후):
#   import pyperclip
#   def copy_to_clipboard(text):
#       pyperclip.copy(text)
# 이 경우 widget 인자가 필요 없어진다. (Tkinter 에 의존하지 않음)
