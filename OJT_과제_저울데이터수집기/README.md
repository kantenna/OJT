# 표준 통합 저울 데이터 수집 프로그램

전자저울이 USB-Serial 로 보내는 무게 데이터를 PC가 받아 → 무게 숫자만 추출 →
화면 표시 + 클립보드 자동 복사 하는 데스크톱 프로그램.

작업자는 ERP 입력란에서 `Ctrl+V` 한 번으로 무게를 입력할 수 있다.

```
저울 ─(USB-Serial)─> PC → [내 프로그램] → 무게 추출 → 클립보드 → ERP 붙여넣기
```

## 주요 기능

- **시리얼 수신**: 선택한 COM 포트에서 저울 데이터를 백그라운드 스레드로 수신
- **무게 추출(파싱)**: `ST,GS,   37.39,kg` 형식에서 무게(`37.39`)와 안정/흔들림 상태를 추출
- **GUI 표시**: 무게를 크게 표시, 안정(초록 ●)/흔들림(주황 ●) 상태 구분
- **클립보드 자동 복사**: 안정 상태일 때 무게를 자동 복사 (같은 값 반복 복사는 생략)
- **설정 저장**: 마지막에 쓴 포트·옵션을 `config.json` 에 기억 (다음 실행 시 자동 선택)
- **로깅**: 포트 열림·닫힘, 시작·정지, 연결 끊김 등을 `logs/` 에 날짜별로 기록
- **예외 처리**: 포트 점유·케이블 분리·설정 파일 손상 시에도 죽지 않고 복구

## 폴더 구조

```
.
├── src/                          # 소스 코드 (역할별 분리)
│   ├── main.py                   # 진입점
│   ├── serial_reader.py          # 시리얼 수신 (백그라운드 스레드)
│   ├── scale_parser.py           # 무게 추출 + 체크섬 검증
│   ├── gui.py                    # Tkinter 화면
│   ├── clipboard_util.py         # 클립보드 복사
│   ├── config_manager.py         # 설정 파일 읽기/쓰기
│   ├── app_logger.py             # 로깅 설정 (파일 + 콘솔)
│   └── paths.py                  # 실행 환경별 기준 경로 (소스/배포)
├── simulator/
│   └── simulator.py              # 파이썬 가상 저울 (가상 포트로 테스트)
├── arduino_scale_simulator/
│   └── arduino_scale_simulator.ino   # 아두이노 스케치 (실물 신호 검증)
├── logs/                         # 로그 출력 폴더 (.log 는 git 제외)
├── config.json                   # 포트/보드레이트 등 설정
├── requirements.txt              # 의존성 목록
├── 개발가이드.md                  # 학습 정리 / 단계별 가이드
└── OJT_과제_저울데이터수집기.md     # 원본 과제
```

## 설치

Python 3.10+ 권장.

```
pip install -r requirements.txt
```

> 클립보드 복사는 Python 기본 내장 Tkinter 를 사용한다(별도 설치 불필요).
> `pyserial` 은 시리얼 통신에, `pyinstaller` 는 배포(exe) 단계에만 필요하다.

## 실행 / 사용법

```
python src/main.py
```

1. **포트** 콤보박스에서 저울이 연결된 COM 포트를 선택 (없으면 **새로고침**)
2. **시작** 클릭 → 무게가 실시간으로 표시됨
   - 안정(`ST`) → 초록 "● 안정", 흔들림(`US`) → 주황 "● 흔들림"
3. **안정될 때 자동 복사** 가 켜져 있으면, 안정 상태의 무게가 자동으로 클립보드에 복사됨
4. ERP/메모장 등에서 **Ctrl+V** → 무게 숫자가 붙여넣어짐
5. **정지** 로 수신 중단, 창을 닫으면 설정이 저장되고 종료

> ⚠️ 한 COM 포트는 한 프로그램만 열 수 있다. 아두이노 IDE 시리얼 모니터 등이
> 포트를 잡고 있으면 먼저 닫아야 한다.

## 설정 (config.json)

프로그램이 시작할 때 읽고, 포트 변경·자동복사 토글·종료 시 자동 저장된다.
파일이 없거나 손상되면 기본값으로 복구된다.

| 키 | 의미 | 기본값 |
|----|------|--------|
| `port` | 마지막에 사용한 포트 (자동 선택용) | `""` |
| `baudrate` | 통신 속도 | `9600` |
| `copy_only_when_stable` | 안정 상태일 때만 복사 | `true` |
| `bytesize` / `parity` / `stopbits` | 통신 파라미터 (현재 8/N/1 기본 사용) | `8` / `"N"` / `1` |
| `manufacturer` | 저울 제조사 | `"CAS"` |

## 로그 (logs/)

`logs/scale_YYYY-MM-DD.log` 에 날짜별로 쌓이며, 콘솔에도 동시 출력된다.
현장 배포(--windowed exe) 시 콘솔이 없어도 파일로 동작을 추적할 수 있다.

기록 예시:

```
14:32:07 INFO    [main]   프로그램 시작 (로그 파일: ...)
14:32:09 INFO    [gui]    시작 요청: COM4
14:32:09 INFO    [serial] COM4 포트 열림 (9600bps)
14:35:11 INFO    [gui]    사용자 정지
14:35:11 INFO    [serial] COM4 포트 닫힘 (수신 종료)
14:40:02 ERROR   [serial] 연결 끊김: COM4 (케이블 분리 추정)
```

> 무게 한 줄 한 줄은 기록하지 않는다(로그 폭증 방지). 포트·시작/정지·에러 같은
> 핵심 사건만 남는다. "정지(INFO)" 와 "연결 끊김(ERROR)" 이 등급으로 구분된다.

## 하드웨어 없이 테스트 (시뮬레이터)

저울 없이 파이썬 시뮬레이터로 저울 신호를 흉내 낸다.
[com0com](https://sourceforge.net/projects/com0com/) 등으로 가상 포트 쌍(예: COM5↔COM6)을
만든 뒤, 터미널 2개로 송신/수신을 분리해 실행한다.

```
# 터미널 A — 저울 역할(송신, 체크섬 포함 CAS 형식)
python simulator/simulator.py COM4

# 터미널 B — 내 프로그램(반대쪽 COM5 수신)
python src/main.py
```

> 시뮬레이터는 `scale_parser.append_checksum()` 으로 NMEA 체크섬을 붙여 보내고,
> 수신측 `parse_weight()` 가 이를 검증한다(체크섬 없는 신호도 하위호환으로 허용).

## 실물 신호 검증 (아두이노)

`arduino_scale_simulator/arduino_scale_simulator.ino` 를 Arduino UNO 에 업로드하면
9600bps 로 CAS 형식 문자열을 1초마다 송신한다. 업로드 후 **시리얼 모니터를 닫고**
프로그램에서 해당 COM 포트를 선택해 테스트한다.

## 배포 (exe 만들기)

현장 PC 에 Python 이 없어도 실행되도록 [PyInstaller](https://pyinstaller.org/) 로
하나의 `.exe` 로 묶는다. **프로젝트 루트**(이 README 가 있는 폴더)에서 실행한다.

```
pip install pyinstaller
python -m PyInstaller --onefile --windowed --name 저울데이터수집프로그램 src/main.py
```

- `--onefile` : 파일 하나(.exe)로 묶기
- `--windowed` : 콘솔창 없이 GUI 만 실행
- `--name` : 결과 exe 이름
- `python -m PyInstaller` : `pyinstaller` 명령이 PATH 에 없을 때도 동작

빌드 결과:

```
dist/
└── 저울데이터수집프로그램.exe
```

### 배포 패키지 구성

exe 만으로는 부족하다. `config.json` 을 **exe 와 같은 폴더**에 둬야 한다.
(코드가 frozen 상태에서는 exe 위치 기준으로 config·logs 를 찾는다 — `src/paths.py`)

```
배포폴더/
├── 저울데이터수집프로그램.exe
├── config.json              # 현장에서 포트만 바꾸면 됨
└── logs/                    # 실행 시 자동 생성, 동작 로그가 쌓임
    └── scale_YYYY-MM-DD.log
```

이 폴더째 현장 PC 로 복사하면 더블클릭으로 실행된다.

> 빌드 부산물 `build/`, `dist/`, `*.spec` 은 `.gitignore` 로 git 에서 제외된다.

## 데이터 형식 / 지원 저울

- CAS (CK200SC): `ST,GS,   37.39,kg`
  - `ST` = Stable(안정) / `US` = Unstable(흔들림)
  - `GS` = Gross(총중량)
  - `37.39` = 추출 대상 무게 / `kg` = 단위

## 개발 순서

자세한 단계별 설명은 [개발가이드.md](개발가이드.md) 참고.

환경준비 → 시리얼 수신 → 시뮬레이터 테스트 → 파싱 → GUI →
멀티스레드 → 클립보드 → 설정/로그/예외 → 아두이노 검증 → exe 배포
