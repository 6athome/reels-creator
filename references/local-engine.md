# 로컬 릴스 제작 엔진

Codex가 사용자 요청과 확인한 자료를 바탕으로 기획안을 작성합니다. Python은 파일 목록·미디어 정보 확인, 기본 파일 순서 계획, 시간 및 경로 검증, 작업 폴더 준비를 맡습니다. Remotion은 승인된 JSON으로 MP4와 표지를 렌더링합니다.

## 자연어 요청 예시

> 이 폴더의 사진과 영상으로 30초 릴스를 만들어줘. 첫 3초는 강하게 후킹하고, EUN.PANCHI 스타일로 편집해줘. 기획안부터 보고 승인할게.

Codex는 먼저 `plan`으로 초안을 생성하고, 사용자가 알려 준 장면과 타임코드, 직접 본 이미지·대표 프레임을 근거로 제목, 타깃, 훅, 스토리, 컷, 자막과 표지 문구를 구체화합니다. 움직임이나 대사의 타이밍을 선택한 정지 프레임만으로 확정하기 어려우면 사용자가 제공한 타임코드를 사용합니다. 영상 내용을 볼 수 없을 때는 파일 순서 계획을 사용하거나 설명을 요청합니다. `planningBasis`에 편집 근거를 기록합니다.

## 실행

스킬 폴더 기준 예시입니다. Windows는 `py -3`, macOS는 `python3`를 사용할 수 있습니다. 작업 폴더에 결과를 남기려면 `--output`을 지정합니다. Codex가 사용자 대신 실행할 수 있습니다.

```powershell
py -3 scripts/reel_engine.py auto '<입력 폴더>' --project-id my-reel --title '오늘의 기록' --hook '처음 본 순간' --seconds 30
py -3 scripts/reel_engine.py plan '<입력 폴더>' --project-id my-reel --title '오늘의 기록' --seconds 30
py -3 scripts/reel_engine.py validate 'output/my-reel/v001/reel-project.json'
py -3 scripts/reel_engine.py render 'output/my-reel/v001/reel-project.json'
py -3 scripts/reel_engine.py render 'output/my-reel/v001/reel-project.json' --cover-only
```

- `auto`는 폴더를 재귀 스캔해 파일명 순으로 계획하고 바로 렌더링합니다. 기본 계획은 원본 범위에서 목표 시간을 균등 분배합니다. 합계가 부족하면 목표를 줄이거나 자료를 추가합니다. 제목 이후에는 파일명 자막을 사용하며, 순서를 바꾸고 싶다면 JSON을 수정합니다.
- `plan`은 검증된 초안과 매니페스트까지만 작성합니다. 초안을 고친 뒤 `validate`로 검사하고 `render`를 실행하면 새 버전을 생성합니다. 영상 길이는 30fps 프레임 단위로 지정합니다.
- `--fit cover`는 원본 비율을 유지하면서 세로 화면을 채웁니다. `--fit blur`는 원본 비율로 중앙에 배치하고 같은 미디어를 확대·흐림 처리해 여백을 채웁니다. `--fit contain`은 단색 여백을 둡니다. 사진은 `--photo-motion`으로 정지·줌·좌우 팬을 선택합니다. 컷별 `objectPosition`으로 초점을 옮길 수 있고, 모든 전환은 하드컷입니다.
- 표지는 `--cover-photo`로 지정한 사진, `--cover-video`와 `--cover-time`으로 지정한 영상 프레임, 재생 순서상 첫 사용 가능 사진 또는 첫 영상 프레임 순으로 선택합니다. 기본 선택은 화면 내용을 평가하지 않습니다. `--cover-position`에 CSS 위치 값(예를 들어 `"55% 50%"`)을 지정해 크롭 중심을 조정하세요. 기존 글자가 있는 표지는 `--cover-native-text`로 새 제목과 어두운 그라데이션을 생략할 수 있습니다.
- `--music`에 사용할 권한이 있는 로컬 음악 파일을 지정할 수 있습니다. 짧은 트랙은 반복합니다. `--mute-source`, `--source-volume`, `--music-volume`, `--fade-out`으로 원본 오디오, 배경음악과 종료 페이드 프레임을 조절합니다.
- 렌더는 이미 설치된 Remotion Chromium을 우선 찾습니다. 다른 설치를 사용할 때는 `--browser`에 실행 파일을 지정합니다. 이 작업 폴더에서는 기존 전체 FFmpeg를 프로젝트 내부 `.local-tools/ffmpeg/`에 복사해 WebP까지 디코딩할 수 있도록 했습니다. 새 환경에서는 전체 FFmpeg와 ffprobe를 PATH에서 사용합니다. 환경에 따라 기본 샌드박스에서는 네이티브 실행 승인 절차가 필요할 수 있습니다.

## 기획안 JSON

### 자막 컬러

새 계획의 `captionColorMode`는 기본 `auto`입니다. 화면을 보고 선택하기 어려우면 검정·흰색만 비교합니다. 렌더 후 실제 선택과 근거는 `caption-color-report.json`에 들어 있습니다. 명시적 요청은 `--caption-color black`처럼 실행하거나 계획에 `captionColorMode: "manual"`과 `captionColorPreset`을 저장합니다. 가능한 기본값은 `white`, `black`, `burgundy`, `lime`, `sky-blue`, `soft-pink`입니다. 작은 강조에는 기존 개별 자막 스타일을 사용하고, 기본은 영상 전체에 조합 하나입니다.

새 조합은 `config/caption-colors.local.json`에 기본 팔레트와 다른 이름으로 추가합니다. 예를 들어 `{"ink": {"captionBackgroundColor": "#171717", "captionTextColor": "#FDF7ED", "captionBackgroundOpacity": 0.96}}`입니다. 기존 JSON에 컬러 설정이 없으면 이전 버건디 기본값과 개별 스타일을 유지합니다. AUTO로 전환하려면 모드를 `auto`로 바꾸고 명시적 계획 컬러 필드를 삭제하세요. 계획에 명시한 색보다 개별 컷의 명시적 색이 우선합니다.

Codex가 대표 장면을 실제로 검토한 경우에만 `planningBasis: "visually-reviewed"`, `captionAccent`, `captionAccentReason`으로 포인트 색을 추천할 수 있습니다. 엔진은 여러 샘플의 색 분포가 안정적이고 배경과의 구분과 글자 대비를 충족할 때만 적용합니다. 대비비는 저해상도 대표 프레임에 반투명 박스를 합성한 추정치입니다. 움직이는 배경 전수 검사나 WCAG 인증으로 해석할 수 없습니다. [WCAG 대비 기준](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)

`save-style my-style examples/personal-style.json`으로 별도 개인 설정을 등록합니다. 새 기획안에는 `--personal-style my-style`, 기존 기획안에는 `"personalStyle": "my-style"`을 사용합니다. 기본 적용 순서는 내장 프리셋, 개인 스타일, 해당 큐나 표지의 개별 설정입니다. 폰트 후보, 글씨 크기·색, 자막 위치·배경·패딩, 표지 프리셋·레이어 위치를 저장할 수 있습니다. 사용 권한이 있는 폰트 파일은 `remotion/public/fonts/`에 넣고 `config/local-fonts.json`에 `{"family":"My Font","file":"fonts/my-font.woff2","weight":"300 700"}` 형식으로 등록합니다.

[검증 스키마](../config/reel-project.schema.json)를 사용합니다. `sourceStart`와 `sourceEnd`는 원본 초 단위이고, 종료는 제외됩니다. `timelineStartFrame`과 `durationFrames`는 타임라인의 프레임 단위입니다. 컷 순서를 바꿀 때 각 컷 시작 프레임을 앞선 길이의 합으로 재계산하고, 길이를 바꿀 때 후속 자막과 `targetDuration`도 확인합니다.

자막의 `style: {}`는 Signature 프리셋을 그대로 따릅니다. 얼굴이나 제품을 가리면 해당 큐의 `style.y`를 조정합니다. `cover.text`는 프리셋 레이어별 텍스트이며 기존 글자를 쓰려면 빈 객체를 지정합니다. Bold Hook은 `title`과 선택적 `subtitle`, Storytelling은 `title`, Playful Impact는 `keyword`와 선택적 `lead-1`, `lead-2`, `lead-3`를 사용합니다. 표지 사진 또는 영상 스틸은 `assetId`와 `sourceTime`으로 선택합니다. 글자가 기본 레이아웃보다 길면 정해진 범위 안에서 글자 크기를 줄이고, 그 범위를 넘어가면 문구를 줄이거나 줄바꿈·폭을 조정하도록 오류를 표시합니다. `references/user-samples/`의 파일은 스타일 검토에 사용합니다.

## 결과와 분석 범위

`output/<projectId>/vNNN/`에 `reel.mp4`, `cover.png`, `reel-project.json`, `captions.json`, `render-report.json`과 `media-manifest.json`을 저장합니다. 렌더 완료 뒤 영상 코덱·크기·프레임레이트·프레임 수·오디오 유무와 PNG 크기를 확인합니다.

스캐너는 FFprobe의 메타데이터와 FFmpeg 첫 프레임 디코딩으로 초기 파일 오류를 발견합니다. 첫 프레임 이후 손상은 렌더 때 드러날 수 있습니다. 영상의 내용, 발화, 감정, 하이라이트는 스캐너가 판정하지 않습니다. 사용자가 내용을 설명하거나 Codex가 실제로 확인한 이미지와 프레임을 편집 근거로 씁니다.
