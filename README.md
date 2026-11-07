# Camera Recorder

실험용 카메라 녹화 프로그램입니다. 카메라를 고르고, 화면을 보면서 버튼 하나로 녹화합니다.

Ubuntu 24.04에서 확인했습니다. USB 웹캠은 실제 카메라로 검증했고, Intel RealSense는 아직 실제 장치로 검증하지 못했습니다.

## 설치

처음 한 번만 하면 됩니다. 디스크 공간이 약 650MB 필요합니다.

**1.** 터미널을 열고(`Ctrl`+`Alt`+`T`) 아래 두 줄을 실행합니다. 비밀번호를 물으면 컴퓨터 로그인 비밀번호를 입력합니다.

```bash
sudo apt install -y git curl v4l-utils libxcb-cursor0
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**2.** 터미널을 닫았다가 다시 열고 아래 네 줄을 실행합니다.

```bash
git clone https://github.com/nayana224/camera_recorder.git ~/camera_recorder
cd ~/camera_recorder
uv sync --extra realsense
uv run camrec install-app
```

## 사용

**1.** 키보드의 Super(윈도우) 키를 누르고 `카메라 레코더`를 검색해서 실행합니다. 영어 환경에서는 `Camera Recorder`로 검색합니다.

**2.** 카메라 화면이 나오면 `해상도`를 고릅니다. 카메라가 보이지 않으면 연결한 뒤 `스캔`을 누릅니다.

**3.** `녹화 시작`을 누릅니다. 끝나면 `녹화 중지`를 누릅니다. Space 키로도 됩니다.

**4.** 오른쪽 기록 창에서 결과를 확인합니다. `estimated_dropped_frames=0`이면 빠진 프레임 없이 녹화된 것입니다.

영상은 `~/camera_recorder/recordings/`에 시각별 폴더로 저장되고, 영상 파일 이름은 `video.mkv`입니다.
1080p 기준으로 1분에 약 670MB를 쓰니 저장 공간을 확인해 주세요.

## 문제가 생겼을 때

| 증상 | 해결 방법 |
|---|---|
| `uv: command not found` | 터미널을 닫았다가 다시 열고 실행 |
| 앱 메뉴에 보이지 않음 | 로그아웃했다가 다시 로그인 |
| `Qt needs libxcb-cursor` 알림 | `sudo apt install -y libxcb-cursor0` 실행 |
| `카메라 0대 발견` | USB를 다시 꽂고 `스캔` 클릭 |
| `Device or resource busy` | 카메라를 쓰는 다른 프로그램을 닫고 `스캔` 클릭 |
| `Permission denied` | `sudo usermod -aG video $USER` 실행 후 다시 로그인 |
| 녹화할 수 있는 모드가 없음 | MJPEG를 지원하는 카메라가 필요합니다 |

## 업데이트

```bash
cd ~/camera_recorder
git pull
uv sync --extra realsense
```

## 삭제

녹화 파일도 함께 지워지니 `~/camera_recorder/recordings/`를 먼저 옮겨 두세요.

```bash
cd ~/camera_recorder
uv run camrec uninstall-app
cd ~
rm -rf ~/camera_recorder
```

## 더 알아보기

터미널 명령, 카메라 설정 고정, RealSense, 새 카메라 추가는 [고급 사용법](docs/advanced.md)을 보세요.
