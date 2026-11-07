# Camera Recorder

실험용 카메라 녹화 프로그램입니다. 연결된 카메라를 찾아서 고르고, 화면을 보면서 해상도를 정해 녹화합니다.
Ubuntu 앱 메뉴에 등록해 다른 프로그램처럼 아이콘으로 실행할 수 있습니다.

| 카메라 | 저장 형식 | 상태 |
|---|---|---|
| USB 웹캠 (`webcam`) | MJPEG 원본 `.mkv` + 프레임별 타임스탬프 | 실제 카메라로 검증 |
| Intel RealSense (`realsense`) | SDK `.bag` (컬러 + 깊이) | **실제 장치로 미검증** |

## 처음 설치하기

Ubuntu 기준입니다. 터미널을 열고 아래 순서대로 한 번씩만 실행하면 됩니다.

### 1. 필요한 시스템 패키지 설치

```bash
sudo apt install git v4l-utils libxcb-cursor0
```

비밀번호를 물으면 이 컴퓨터의 로그인 비밀번호를 입력합니다. 입력해도 화면에는 표시되지 않습니다.

### 2. uv 설치

Python 패키지를 관리하는 도구입니다. `uv --version`이 이미 동작하면 건너뜁니다.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

설치한 뒤 터미널을 닫았다가 다시 엽니다.

### 3. 프로그램 내려받기

```bash
git clone https://github.com/nayana224/camera_recorder.git
cd camera_recorder
uv sync --extra realsense
```

RealSense를 쓰지 않으면 마지막 줄은 `uv sync`만 실행해도 됩니다.

### 4. 앱 메뉴에 등록

```bash
uv run camrec install-app
```

`warning`이 나오면 그 줄에 적힌 명령을 실행합니다. 1번 단계를 건너뛰었을 때 나타납니다.

### 5. 실행

키보드의 Super(윈도우) 키를 누르고 `카메라 레코더`를 검색해서 실행합니다.
자주 쓴다면 실행 중인 아이콘을 우클릭해서 `대시에 고정`을 선택하세요.

## 녹화하기

1. 앱을 실행하면 카메라를 자동으로 찾아서 화면을 보여 줍니다.
   나중에 연결한 카메라는 `스캔`을 누르면 나타납니다.
2. `해상도`와 `FPS`를 고릅니다. 카메라가 지원하는 값만 표시되고, 고르면 화면이 잠깐 끊겼다가 다시 나옵니다.
3. 필요하면 `라벨`에 시험 이름을 적습니다. 저장 폴더 이름에 붙습니다. 예: `trial_01`
4. `녹화 시작`을 누르거나 Space 키를 누릅니다.
5. 끝나면 `녹화 중지`를 누르거나 Space 키를 다시 누릅니다.
6. 오른쪽 기록 창에서 저장 위치와 결과를 확인합니다.

```text
frames=182, duration_s=6.032, mean_fps=30.007, estimated_dropped_frames=0
```

`mean_fps`가 설정한 FPS와 비슷하고 `estimated_dropped_frames`가 0이면 빠진 프레임 없이 녹화된 것입니다.
어두운 곳에서 자동 노출을 쓰면 FPS가 낮아질 수 있습니다.

알아 두면 좋은 점:

- 녹화 중에는 카메라와 해상도를 바꿀 수 없습니다.
- 녹화 중에 창을 닫으면 녹화를 끝낼지 먼저 묻습니다.
- 녹화 중 카메라가 끊겨도 그때까지 받은 영상은 저장됩니다.
- 화면의 빨간 `REC` 글자는 녹화 영상에 들어가지 않습니다.
- 기본 저장 위치는 프로그램 폴더 안의 `recordings/`이고, `저장 위치`에서 바꿀 수 있습니다.

## 문제가 생겼을 때

| 증상 | 해결 방법 |
|---|---|
| 아이콘을 눌렀는데 `Qt needs libxcb-cursor` 알림이 뜬다 | `sudo apt install libxcb-cursor0` 실행 |
| 앱 메뉴에 보이지 않는다 | `uv run camrec install-app`을 다시 실행하고, 로그아웃했다가 다시 로그인 |
| `카메라 0대 발견`이라고 나온다 | USB를 다시 꽂고 `스캔`을 누름. 그래도 없으면 터미널에서 `v4l2-ctl --list-devices`로 확인 |
| `Device or resource busy` 오류가 나온다 | 카메라를 쓰는 다른 프로그램(화상회의, Cheese, 다른 Camera Recorder 창)을 닫고 `스캔`을 누름 |
| `Permission denied` 오류가 나온다 | `sudo usermod -aG video $USER` 실행 후 로그아웃했다가 다시 로그인 |
| 녹화할 수 있는 모드가 없다고 나온다 | MJPEG를 지원하지 않는 카메라입니다. 이 프로그램은 MJPEG만 저장합니다 |
| 녹화를 시작하지 못했다고 나온다 | `저장 위치`가 쓸 수 있는 폴더인지 확인 |
| 프로그램 폴더를 옮긴 뒤 아이콘이 동작하지 않는다 | 옮긴 폴더에서 `uv sync --extra realsense`와 `uv run camrec install-app`을 다시 실행 |

## 업데이트와 삭제

새 버전으로 업데이트하기:

```bash
git pull
uv sync --extra realsense
```

앱 메뉴에서 없애기:

```bash
uv run camrec uninstall-app
```

프로그램을 완전히 지우려면 그다음 `camera_recorder` 폴더를 삭제합니다.
녹화 파일도 그 폴더의 `recordings/`에 있으니 먼저 옮겨 두세요.

## 터미널에서 사용하기

앱 없이 명령어로도 녹화할 수 있습니다.

```bash
uv run camrec list                         # 설정과 연결된 카메라 확인
uv run camrec gui                          # 앱 창 열기
uv run camrec record webcam                # 프리뷰, Space로 녹화 시작/정지, q 또는 Esc로 종료
uv run camrec record webcam -l trial_01    # 세션 폴더 이름에 라벨 추가
uv run camrec record webcam -d 30          # 바로 녹화 시작, 30초 후 정지
uv run camrec record webcam --no-preview   # 창 없이 녹화, Ctrl+C로 정지
```

## 녹화 결과물

```text
recordings/webcam/20261106_215603_trial_01/
├── video.mkv         카메라가 보낸 MJPEG 그대로 (재인코딩 없음)
├── timestamps.csv    프레임 번호, 촬영 시각(Unix), 영상 내 시각
└── metadata.json     설정, 실제 카메라 컨트롤 값, 프레임 수, 평균 fps, 드롭 추정치
```

- 다른 데이터와 시간을 맞출 때는 `timestamps.csv`의 `timestamp_unix_s`를 씁니다. 커널이 프레임을 받은 시각입니다.
- 1080p 30fps 기준 약 11 MB/s(분당 약 670 MB)이며 장면에 따라 달라집니다.

## 카메라 설정 파일

`configs/`의 설정 파일은 선택 사항입니다. 없어도 앱은 동작하지만, 있으면 앱과 명령어가 같은 설정을 씁니다.

- 앱에서 고른 카메라와 같은 장치의 설정 파일이 있으면 그 파일의 `controls`와 해상도를 쓰고,
  `recordings/<설정 파일 이름>/`에 저장합니다.
- 설정 파일이 없으면 자동 노출로 찍고 `recordings/<카메라 이름>/`에 저장합니다.
- 앱에서 고른 해상도는 설정 파일에 저장되지 않습니다. 세션의 `metadata.json`에만 남습니다.

같은 종류의 카메라를 더 쓰려면 설정 파일만 추가합니다. 예를 들어 `configs/webcam_top.yaml`을 만들면
`camrec record webcam_top`으로 녹화되고 결과는 `recordings/webcam_top/`에 저장됩니다.

### 웹캠 설정 메모

- `device`에는 `/dev/video0` 대신 `/dev/v4l/by-id/...` 경로를 씁니다. RealSense를 연결하면 `video` 번호가 바뀝니다.
- 똑같은 웹캠을 두 대 쓰면 by-id 경로가 겹칠 수 있습니다. 그때는 USB 포트 기준인 `/dev/v4l/by-path/...`를 씁니다.
- 기본값은 자동 노출, 자동 화이트밸런스, 자동 초점입니다. 실험 내내 화면이 일정해야 하면
  `configs/webcam.yaml`의 `controls` 예시를 켭니다. 이 값은 녹화가 끝나도 카메라에 남습니다.

### RealSense 메모

이 백엔드는 장치 없이 작성했습니다. 처음 연결하면 `camrec record realsense -d 5`로 `.bag`이 정상인지 먼저 확인합니다.

- 일반 사용자 권한으로 쓰려면 librealsense udev 규칙이 필요합니다.
- 깊이 스트림은 USB 3 포트에 연결해야 합니다.
- `.bag` 기록을 켜고 끄려면 파이프라인을 재시작해야 해서 녹화 시작과 정지 때 스트림이 잠깐 끊깁니다.
- 앱에서는 컬러와 깊이에 같은 해상도를 쓰므로, 둘이 공통으로 지원하는 모드만 표시됩니다.
  서로 다른 해상도가 필요하면 `configs/realsense.yaml`을 고쳐서 `camrec record`로 녹화합니다.

## 개발자용

```text
configs/<카메라>.yaml                  카메라 하나당 설정 파일 하나
recordings/<카메라>/<세션>/            설정 파일 이름별로 저장
src/camera_recorder/
├── cli.py                             camrec 명령
├── gui.py                             앱 창
├── desktop.py                         앱 메뉴 등록
├── session.py                         녹화 루프, 세션 폴더, metadata.json (카메라 공통)
└── cameras/
    ├── __init__.py                    백엔드 목록
    ├── base.py                        모든 백엔드가 구현하는 인터페이스
    ├── webcam/
    └── realsense/
```

새 카메라 종류를 추가하려면:

1. `src/camera_recorder/cameras/<종류>/`를 만들고 `base.py`의 `Camera`를 구현합니다.
2. `cameras/__init__.py`의 `BACKENDS`에 등록합니다.
3. SDK가 필요하면 `pyproject.toml`의 `optional-dependencies`에 추가합니다.
4. `configs/<카메라>.yaml`을 만들고 `backend:`에 종류를 적습니다.
