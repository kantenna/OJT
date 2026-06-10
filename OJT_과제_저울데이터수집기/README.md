# 표준 통합 저울 데이터 수집 프로그램

전자저울이 USB-Serial 로 보내는 무게 데이터를 PC가 받아 → 무게 숫자만 추출 →
화면 표시 + 클립보드 자동 복사 하는 데스크톱 프로그램.

작업자는 ERP 입력란에서 `Ctrl+V` 한 번으로 무게를 입력할 수 있다.

```
저울 ─(USB-Serial)─> PC → [내 프로그램] → 무게 추출 → 클립보드 → ERP 붙여넣기
```

## 폴더 구조

```
.
├── src/                          # 소스 코드 (역할별 분리)
│   ├── main.py                   # 진입점
│   ├── serial_reader.py          # 시리얼 수신 (백그라운드 스레드)
│   ├── parser.py                 # 무게 추출 (정규식)
│   ├── gui.py                    # Tkinter 화면
│   ├── clipboard_util.py         # 클립보드 복사
│   └── config_manager.py         # 설정 파일 읽기/쓰기
├── simulator/
│   └── scale_simulator.py        # 파이썬 가상 저울 (하드웨어 없이 테스트)
├── arduino_scale_simulator/
│   └── arduino_scale_simulator.ino   # 아두이노 스케치 (실물 신호 검증)
├── logs/                         # 로그 출력 폴더
├── config.json                   # 포트/보드레이트 등 설정
├── requirements.txt              # 의존성 목록
├── 개발가이드.md                  # 학습 정리 / 단계별 가이드
└── OJT_과제_저울데이터수집기.md     # 원본 과제
```

## 설치

```
pip install -r requirements.txt
```

## 실행

```
python src/main.py
```

## 하드웨어 없이 테스트 (시뮬레이터)

저울 없이 파이썬 시뮬레이터로 저울 신호를 흉내 낸다.
[com0com](https://sourceforge.net/projects/com0com/) 등으로 가상 포트 쌍(예: COM5↔COM6)을
만든 뒤, 터미널 2개로 송신/수신을 분리해 실행한다.

```
# 터미널 A — 저울 역할(송신)
python simulator/scale_simulator.py COM5

# 터미널 B — 내 프로그램(COM6 수신)
python src/main.py
```

> 인자 없이 실행하면 현재 PC의 COM 포트 목록을 보여준다: `python simulator/scale_simulator.py`
> 실물 신호 검증은 `arduino_scale_simulator/` 의 아두이노 스케치로 수행한다.

## 개발 순서

자세한 단계별 설명은 [개발가이드.md](개발가이드.md) 참고.

환경준비 → 시리얼 수신 → 시뮬레이터 테스트 → 파싱 → GUI →
멀티스레드 → 클립보드 → 설정/로그/예외 → 아두이노 검증 → exe 배포

## 지원 저울

- CAS (CK200SC):  `ST,GS,   37.39,kg`
