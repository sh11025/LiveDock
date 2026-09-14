# 📺 LiveDock (라이브도크)

> **치지직(CHZZK) · SOOP · 유튜브(YouTube)** 실시간 스트리밍 서버 상태 모니터링 & 온에어(Live) 알림 플로팅 데스크톱 위젯

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/GUI-PyQt6-41CD52?style=for-the-badge&logo=qt&logoColor=white" alt="PyQt6" />
  <img src="https://img.shields.io/badge/Platform-Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white" alt="Platform" />
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="License" />
</p>

---

## 📖 프로젝트 소개

**LiveDock**은 웹 브라우저를 계속 켜놓거나 탭을 일일이 새로고침하지 않고도, 바탕화면 한구석에 작고 깔끔한 도크(Dock) 형태로 띄워두고 **선호하는 스트리머의 방송 시작 여부**와 **주요 스트리밍 플랫폼(치지직, SOOP, 유튜브)의 중계 서버 상태**를 한눈에 실시간 모니터링할 수 있는 윈도우용 경량 위젯입니다.

---

## ✨ 주요 기능

### 1. 🟢 실시간 플랫폼 서버 헬스체크 & 장애 알림
- **치지직(CHZZK), SOOP, 유튜브(YouTube)** 의 중계 세션 응답 속도(Latency, ms)를 주기적으로 자동 측정합니다.
- 정상(초록), 지연(노랑), 장애/단절(빨강)의 3단계 상태 인디케이터를 제공합니다.
- 서버 세션에 장애가 감지되거나 심한 지연이 발생할 경우, **윈도우 시스템 트레이 팝업 알림**으로 즉시 경고합니다.
- 상단 서버 버튼 클릭 시 해당 스트리밍 플랫폼 메인 페이지로 즉시 이동합니다.

### 2. 🔴 스트리머 온에어(Live) 실시간 감지 & 트레이 알림
- 백그라운드 스레드에서 등록된 스트리머의 방송 상태를 30초마다 자동 폴링(Polling)합니다.
- **오프라인 상태**: 흑백 반투명 처리되어 시각적 피로도를 최소화합니다.
- **방송 시작(온에어) 시**:
  - 시스템 트레이를 통해 **스트리머 이름과 방송 제목이 포함된 윈도우 알림** 발송
  - 프로필 테두리에 플랫폼 고유 컬러(치지직: 민트, SOOP: 블루)가 점등되며 컬러 프로필로 활성화

### 3. 🖱️ 편리한 사용자 인터랙션 & 채널 관리
- **좌클릭**: 해당 스트리머의 실시간 방송 페이지(웹 브라우저)로 원클릭 즉시 이동
- **우클릭**: 간편한 채널 삭제 컨텍스트 메뉴 제공
- **`+` 버튼**: 채널 URL 전체(`https://chzzk.naver.com/live/...` 또는 `https://play.sooplive.com/...`)나 고유 ID만 복사해 붙여넣으면, 플랫폼을 자동 판별하여 프로필 썸네일과 닉네임을 자동 연동 등록

### 4. 🪟 미니멀 프레임리스(Frameless) 플로팅 덱 UI
- 불필요한 타이틀바 없는 현대적인 다크 테마 라운드 디자인
- **마우스 드래그**: 화면 원하는 곳 어디든 자유롭게 이동 배치 가능
- **항상 위(Always on Top)**: 게임, 웹서핑, 작업 중에도 항상 맨 앞에 표시되어 놓치지 않고 확인 가능
- **비동기 이미지 로딩**: 여러 채널을 등록해도 화면 멈춤(UI 프리징) 없는 쾌적한 반응성 제공

---

## 🖥️ 플랫폼별 지원 명세

| 플랫폼 | 서버 헬스체크 | 온에어 실시간 감지 | 채널 추가 지원 포맷 |
| :--- | :---: | :---: | :--- |
| **치지직 (CHZZK)** | O (공통 API 응답속도) | O (Live Status API) | 채널 URL 또는 32자리 고유 해시 ID |
| **SOOP (구 아프리카TV)** | O (플레이어 세션 API) | O (Player Live API) | 방송국 URL 또는 방송국 스트리머 ID |
| **유튜브 (YouTube)** | O (GoogleVideo 리포팅) | - | 상단 서버 상태 인디케이터 전용 |

---

## 🚀 시작하기

### 방법 1. 독립 실행 파일(EXE) 사용
1. 본 저장소의 [Releases](../../releases) 탭에서 최신 버전의 `LiveDock.exe`를 다운로드합니다.
2. 별도의 파이썬 설치 없이 다운로드한 `LiveDock.exe`를 바로 실행하면 동작합니다.

### 방법 2. 소스 코드로 직접 실행

#### 필수 요구사항
- Python 3.9 이상

```bash
# 1. 저장소 복제 (Clone)
git clone https://github.com/사용자계정/저장소이름.git
cd 저장소이름

# 2. 필수 라이브러리 설치
pip install -r requirements.txt

# 3. 프로그램 실행
python multilive_dock_final.py
```

---

## 🛠️ 실행 파일(.exe) 직접 빌드하기

직접 단일 실행 파일로 패키징하려면 `PyInstaller`를 사용할 수 있습니다:

```bash
# PyInstaller 설치
pip install pyinstaller

# 단일 파일(Onefile) 빌드 실행
pyinstaller --noconfirm --onefile --windowed --icon "app_icon.ico" --add-data "app_icon.ico;." --name "LiveDock" multilive_dock_final.py
```
> 빌드가 완료되면 `dist/` 폴더 내에 `LiveDock.exe` 실행 파일이 생성됩니다.

---

## 📁 프로젝트 구조

```text
├── multilive_dock_final.py   # 메인 애플리케이션 및 UI / 백그라운드 스레드 소스
├── app_icon.ico              # 애플리케이션 및 시스템 트레이 아이콘
├── requirements.txt          # Python 필수 라이브러리 목록
├── .gitignore                # Git 추적 제외 설정 파일
├── channels.json             # 사용자 등록 채널 데이터 (자동 생성)
└── README.md                 # 프로젝트 가이드 문서
```

---

## ⚙️ 단축 조작 가이드

- **도크 창 이동**: 도크의 빈 영역을 마우스 왼쪽 버튼으로 누른 채 드래그
- **방송국 바로가기**: 서버 아이콘 또는 스트리머 프로필 좌클릭
- **채널 삭제**: 삭제하려는 스트리머 프로필 우클릭 후 `삭제` 선택
- **도크 닫기**: 우측 상단 `✕` 버튼 클릭

---
## 실제 사례
- **전에 다닌 회사 후임에게 추천**: 인터넷 방송을 송출 하는데. 프로그램 덕에 빠르게 대처 가능했다고 연락이 왔었습니다.

## 📄 라이선스

This project is licensed under the [MIT License](LICENSE).
