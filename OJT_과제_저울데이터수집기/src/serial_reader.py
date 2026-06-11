"""
serial_reader.py — 시리얼(COM 포트) 수신 담당

[1·3·5단계] 백그라운드 스레드에서 포트를 열고 → 한 줄씩 받아 → 파싱해서
            → Queue(큐)에 넣는다. GUI 스레드는 이 큐만 들여다보면 된다.

왜 스레드? readline() 은 데이터가 올 때까지 멈춰 기다린다(블로킹).
GUI 와 같은 곳에서 돌리면 창이 얼어붙으므로, 수신은 별도 스레드로 분리한다.

단독 실행(콘솔 테스트):
    python src/serial_reader.py            (포트 목록만 보여줌)
    python src/serial_reader.py COM4       (그 포트에서 받아서 출력)

관련 개념: pyserial, threading(스레드), queue(큐), 블로킹
"""

import sys
import queue
import logging
import threading

import serial                       # pyserial (설치: pip install pyserial)
from serial.tools import list_ports  # 연결된 COM 포트 목록 조회용

import scale_parser                 # 같은 src 폴더의 scale_parser.py (무게 추출 담당)


def show_ports():
    """현재 PC에 연결된 COM 포트 목록을 출력한다."""
    ports = list_ports.comports()
    if not ports:
        print("사용 가능한 COM 포트가 없습니다. (저울/아두이노 연결 또는 가상 포트 필요)")
        return
    print("사용 가능한 COM 포트:")
    for p in ports:
        print(f"  {p.device}  -  {p.description}")


class SerialReader:
    """
    별도 스레드에서 시리얼 데이터를 계속 받아 큐에 넣는 수신기.

    사용법:
        reader = SerialReader("COM4", 9600)
        reader.start()                 # 백그라운드 수신 시작
        item = reader.queue.get()      # 큐에서 결과 꺼내기 (ScaleReading 또는 ("error", 메시지))
        reader.stop()                  # 수신 중지
    """

    def __init__(self, port, baudrate=9600):
        self.port = port
        self.baudrate = baudrate
        self.queue = queue.Queue()   # 수신 스레드 → GUI 스레드로 결과를 안전하게 전달하는 통로
        self._thread = None
        self._running = False         # 이 깃발이 False가 되면 수신 루프가 멈춘다

    def start(self):
        """백그라운드 수신 스레드를 시작한다."""
        self._running = True
        # daemon=True : 메인 프로그램이 끝나면 이 스레드도 같이 종료된다
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """수신을 멈춘다. (깃발을 내리고 스레드가 끝나길 잠깐 기다림)"""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2)  # 최대 2초 기다림
            self._thread = None

    def _run(self):
        """[스레드에서 도는 함수] 포트를 열고 데이터를 계속 받아 큐에 넣는다."""
        log = logging.getLogger("serial")
        try:
            with serial.Serial(self.port, self.baudrate, timeout=1) as ser:
                log.info("%s 포트 열림 (%dbps)", self.port, self.baudrate)
                ser.reset_input_buffer()   # 잔류 버퍼 제거 → 첫 줄이 이전 데이터와 엉키지 않게
                while self._running:
                    raw = ser.readline()           # 한 줄 대기 (timeout 1초)
                    if not raw:
                        continue                    # 1초간 데이터 없으면 깃발 다시 확인
                    line = raw.decode("ascii", errors="replace").strip()
                    reading = scale_parser.parse_weight(line)
                    if reading is not None:
                        self.queue.put(reading)     # 결과를 큐에 넣음
            # while 가 정상적으로 끝남 = 사용자가 stop() 으로 깃발을 내린 경우
            log.info("%s 포트 닫힘 (수신 종료)", self.port)
        except serial.SerialException as e:
            # 포트가 없거나 다른 프로그램이 점유 중이거나, 수신 중 케이블이 뽑힌 경우
            log.error("연결 끊김: %s (%s)", self.port, e)
            self.queue.put(("error", str(e)))


if __name__ == "__main__":
    # 콘솔에서 단독 테스트: 스레드로 받아서 출력한다.
    if len(sys.argv) < 2:
        show_ports()
        print("\n사용법: python src/serial_reader.py <포트이름>   예) python src/serial_reader.py COM4")
        sys.exit(0)

    reader = SerialReader(sys.argv[1])
    reader.start()
    print(f"[수신 시작] {sys.argv[1]}  (Ctrl+C 로 종료)")
    try:
        while True:
            item = reader.queue.get()   # 큐에서 하나 꺼낼 때까지 대기
            if isinstance(item, scale_parser.WeightData):
                status = "안정" if item.stable else "흔들림"
                print(f"무게: {item.text} {item.unit}  [{status}]")
            else:
                # ("error", 메시지) 형태
                print(f"[에러] {item[1]}")
                break
    except KeyboardInterrupt:
        print("\n[종료] 사용자가 Ctrl+C 를 눌렀습니다.")
    finally:
        reader.stop()
