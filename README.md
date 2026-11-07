# camera_recorder

실험용 카메라 레코더. 카메라마다 설정 파일을 하나 두고, 프리뷰를 보면서 세션 단위로 녹화한다.

| 백엔드 | 저장 형식 | 상태 |
|---|---|---|
| `webcam` (USB, V4L2) | MJPEG 원본 `.mkv` + 프레임별 타임스탬프 | 실제 카메라로 검증 |
| `realsense` | SDK `.bag` (컬러 + 깊이) | **실제 장치로 미검증** |

## 설치

`uv`와 `v4l-utils`(`v4l2-ctl`)가 필요하다.

```bash
uv sync --extra realsense   # RealSense를 쓰지 않으면 --extra 없이
```

## 사용

```bash
uv run camrec list                         # 설정과 연결된 카메라 확인
uv run camrec record webcam                # 프리뷰, Space로 녹화 시작/정지, q 또는 Esc로 종료
uv run camrec record webcam -l trial_01    # 세션 폴더 이름에 라벨 추가
uv run camrec record webcam -d 30          # 바로 녹화 시작, 30초 후 정지
uv run camrec record webcam --no-preview   # 창 없이 녹화, Ctrl+C로 정지
```

프리뷰 창의 `REC` 표시는 화면에만 나오고 녹화본에는 들어가지 않는다.

## 폴더 구조

```text
configs/<카메라>.yaml                  카메라 하나당 설정 파일 하나
recordings/<카메라>/<세션>/            설정 파일 이름별로 저장
src/camera_recorder/
├── cli.py                             camrec 명령
├── session.py                         녹화 루프, 세션 폴더, metadata.json (카메라 공통)
└── cameras/
    ├── __init__.py                    백엔드 목록
    ├── base.py                        모든 백엔드가 구현하는 인터페이스
    ├── webcam/
    └── realsense/
```

같은 종류의 카메라를 더 쓰려면 설정 파일만 추가한다. 예를 들어 `configs/webcam_top.yaml`을 만들면
`camrec record webcam_top`으로 녹화되고 결과는 `recordings/webcam_top/`에 저장된다.

## 웹캠 세션의 결과물

```text
recordings/webcam/20261106_215603_trial_01/
├── video.mkv         카메라가 보낸 MJPEG 그대로 (재인코딩 없음)
├── timestamps.csv    프레임 번호, 촬영 시각(Unix), 영상 내 시각
└── metadata.json     설정, 실제 카메라 컨트롤 값, 프레임 수, 평균 fps, 드롭 추정치
```

- 다른 데이터와 시간을 맞출 때는 `timestamps.csv`의 `timestamp_unix_s`를 쓴다. 커널이 프레임을 받은 시각이다.
- 녹화가 끝나면 `metadata.json`의 `mean_fps`와 `estimated_dropped_frames`를 확인한다.
  어두운 환경에서 자동 노출을 쓰면 프레임레이트가 설정값보다 낮아질 수 있다.
- 1080p 30fps 기준 약 11 MB/s(분당 약 670 MB)이며 장면에 따라 달라진다.

## 웹캠 설정 메모

- `device`에는 `/dev/video0` 대신 `/dev/v4l/by-id/...` 경로를 쓴다. RealSense를 연결하면 `video` 번호가 바뀐다.
- 똑같은 웹캠을 두 대 쓰면 by-id 경로가 겹칠 수 있다. 그때는 USB 포트 기준인 `/dev/v4l/by-path/...`를 쓴다.
- 기본값은 자동 노출, 자동 화이트밸런스, 자동 초점이다. 실험 내내 화면이 일정해야 하면
  `configs/webcam.yaml`의 `controls` 예시를 켠다. 이 값은 녹화가 끝나도 카메라에 남는다.

## RealSense 메모

이 백엔드는 장치 없이 작성했다. 처음 연결하면 `camrec record realsense -d 5`로 `.bag`이 정상인지 먼저 확인한다.

- 일반 사용자 권한으로 쓰려면 librealsense udev 규칙이 필요하다.
- 깊이 스트림은 USB 3 포트에 연결해야 한다.
- `.bag` 기록을 켜고 끄려면 파이프라인을 재시작해야 해서 녹화 시작과 정지 때 스트림이 잠깐 끊긴다.

## 새 카메라 추가

1. `src/camera_recorder/cameras/<종류>/`를 만들고 `base.py`의 `Camera`를 구현한다.
2. `cameras/__init__.py`의 `BACKENDS`에 등록한다.
3. SDK가 필요하면 `pyproject.toml`의 `optional-dependencies`에 추가한다.
4. `configs/<카메라>.yaml`을 만들고 `backend:`에 종류를 적는다.
