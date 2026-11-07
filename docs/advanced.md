# 고급 사용법

일반적인 녹화에는 필요하지 않은 내용입니다. 기본 사용법은 [README](../README.md)를 보세요.

## 터미널에서 사용하기

`~/camera_recorder`에서 실행합니다.

```bash
uv run camrec list                         # 설정과 연결된 카메라 확인
uv run camrec gui                          # 앱 창 열기
uv run camrec record webcam                # 프리뷰, Space로 녹화 시작/정지, q 또는 Esc로 종료
uv run camrec record webcam -l trial_01    # 세션 폴더 이름에 라벨 추가
uv run camrec record webcam -d 30          # 바로 녹화 시작, 30초 후 정지
uv run camrec record webcam --no-preview   # 창 없이 녹화, Ctrl+C로 정지
```

`camrec record`는 `configs/`의 설정 파일이 필요합니다. 포함된 `configs/webcam.yaml`은 특정 웹캠용이므로,
다른 웹캠을 쓸 때는 `camrec list`에 나오는 경로로 `device`를 바꿉니다.

## 앱 동작 참고

- 녹화 중에는 카메라와 해상도를 바꿀 수 없습니다.
- 녹화 중에 창을 닫으면 녹화를 끝낼지 먼저 묻습니다.
- 녹화 중 카메라가 끊겨도 그때까지 받은 영상은 저장됩니다.
- 화면의 빨간 `REC` 글자는 녹화 영상에 들어가지 않습니다.
- 프로그램 폴더를 옮기면 옮긴 폴더에서 `uv sync --extra realsense`와 `uv run camrec install-app`을 다시 실행합니다.

## 녹화 결과물

```text
recordings/webcam/20261106_215603_trial_01/
├── video.mkv         카메라가 보낸 MJPEG 그대로 (재인코딩 없음)
├── timestamps.csv    프레임 번호, 촬영 시각(Unix), 영상 내 시각
└── metadata.json     설정, 실제 카메라 컨트롤 값, 프레임 수, 평균 fps, 드롭 추정치
```

- 다른 데이터와 시간을 맞출 때는 `timestamps.csv`의 `timestamp_unix_s`를 씁니다. 커널이 프레임을 받은 시각입니다.
- `mean_fps`가 설정값보다 낮으면 어두운 환경에서 자동 노출이 프레임레이트를 낮췄을 수 있습니다.

## 카메라 설정 파일

`configs/`의 설정 파일은 선택 사항입니다. 없어도 앱은 동작합니다.

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
