# REELS CREATOR

**v0.6.0-beta.2 · Windows 베타**

사진과 영상이 든 폴더를 알려주면 Codex가 릴스 기획안을 만들고, 컴퓨터에서 세로 MP4와 표지 PNG를 제작합니다. 기획안을 먼저 확인하고, 승인한 뒤 만들 수 있습니다.

## 완성 릴스 예시

**같은 원, 세 가지 리듬**은 배포용 합성 사진 3장으로 만든 15초 무음 릴스입니다. 첫 3초 후킹과 이전 프로젝트의 버건디 자막을 보여 줍니다. 새 프로젝트에는 기본적으로 AUTO 자막 컬러가 적용됩니다.

[예시 MP4 열기](examples/demo-reel.mp4) · [예시 표지 보기](examples/demo-cover.png) · [직접 만드는 합성 샘플](examples/README.md)

## 주요 기능

- 사진·영상 스캔, 기획안 작성, 승인 후 MP4와 표지 출력
- Signature 자막, 흰색·검은색 기본 자동 선택과 검토 근거가 있는 포인트 색, 직접 색상 지정
- 하드컷, 사진 팬·줌, 가로 영상의 세로 크롭 또는 블러 배경
- 원본 소리 유지·음소거, 사용 권한이 있는 배경음악 추가
- 이전 버전을 보존하는 수정 렌더링과 표지 전용 출력

## 설치 방법

1. Codex, Python 3.10+, Node.js 22+ 및 npm 10+, FFmpeg와 ffprobe를 준비합니다. Git은 저장소를 복제할 때 선택적으로 사용합니다.
2. 이 프로젝트의 배포 ZIP을 풀거나 코드를 내려받습니다.
3. [설치 프롬프트](INSTALL_PROMPT.md)를 Codex에 붙여넣고 압축을 푼 폴더 위치를 알려 주세요. 필요한 다운로드는 Codex가 설명한 뒤 승인받아 진행합니다.

Windows에서 직접 설치하려면 압축을 푼 폴더의 PowerShell에서 실행합니다.

```powershell
.\install.ps1 -CheckOnly
.\install.ps1 -Dependencies -InstallBrowser
```

스킬은 기본적으로 `~/.agents/skills/reels-creator`에 설치됩니다. 소프트웨어 배포처는 [Python](https://www.python.org/downloads/) · [Node.js와 npm](https://nodejs.org/en/download) · [FFmpeg와 ffprobe](https://ffmpeg.org/download.html) · [Git](https://git-scm.com/downloads)에서 확인할 수 있습니다. [Codex 스킬 설치 경로](https://developers.openai.com/codex/skills)

## Codex에서 실행하는 방법

아래 [15초 릴스 예시](#실제-영상으로-15초-릴스-만들기)처럼 로컬 작업 공간 경로를 알려 주세요. 제목·첫 문구·컷 순서·자막을 확인한 다음 “이 기획안대로 만들어줘”라고 답하세요.

## 스타일 변경 방법

“자막을 조금 위로 올리고 검정 배경을 써줘”, “표지만 다시 만들어줘”처럼 같은 대화에서 요청하세요. 표지는 정보형 **Bold Hook**, 일상형 **Storytelling**, 반전·공간 공개 **Playful Impact** 중 선택할 수 있습니다. 자주 쓰는 글꼴·색·여백·위치는 별도 개인 프리셋으로 저장할 수 있습니다. [상세 설정](references/local-engine.md)

## 결과물 확인 방법

Codex가 알려 준 영상·표지 링크를 열면 됩니다. 작업 공간의 `output`에 영상과 표지가 저장됩니다. 수정하면 새 버전 폴더가 만들어집니다. `projects`에서 기획안과 자막 색상 선택 이유를 확인할 수 있습니다.

## 자주 묻는 질문

- **스킬이 보이지 않아요.** Codex 새 세션을 열거나 앱을 재시작한 뒤 설치 경로를 확인하세요.
- **기획안만 나오고 영상은 없어요.** 먼저 기획안을 요청했다면 승인 대기 상태입니다. 내용이 괜찮으면 “이 기획안대로 만들어줘”라고 답하세요.
- **도구나 렌더 오류가 나요.** 설치 프롬프트를 Codex에 붙여넣어 누락된 도구를 확인하거나 [문제 해결 가이드](references/troubleshooting.md)를 보세요.

## 지원 환경 및 제한 사항

- **Windows 베타.** Windows 11 x64에서 설치·재설치, 합성 미디어로 기획안 승인·제작·수정, 렌더링을 검증했습니다. 자연어 테스트는 Codex CLI에서 수행했습니다.
- **macOS 설치 스크립트 제공.** Remotion 요구 사항은 macOS 15 이상이며 실제 설치·렌더링은 미검증입니다. [Remotion 요구 사항](https://www.remotion.dev/docs)
- 영상 내용은 Codex가 실제로 확인한 장면이나 사용자가 제공한 설명으로 판단합니다. 인스타그램 자동 업로드와 자동 음성 인식은 지원 범위에 포함되지 않습니다.
- 엔진은 사용자 미디어를 로컬에서 읽고 렌더링합니다. 원본 및 대표 프레임은 채팅에 첨부할 필요가 없습니다. 입력 경로가 포함된 프로젝트 JSON은 로컬에 보관하세요.
- 프로젝트 코드는 [MIT 라이선스](LICENSE)입니다. Remotion 4.0.517은 자체 무료 사용 자격과 배포 조건이 적용됩니다. 패키지에는 Remotion·FFmpeg·Chromium 실행 파일과 폰트 파일이 포함되지 않습니다. [Remotion 4.0.517 라이선스](https://github.com/remotion-dev/remotion/blob/v4.0.517/LICENSE.md) · [사용 조건 안내](https://www.remotion.dev/docs/license/faq)


## 실제 영상으로 15초 릴스 만들기

Git 저장소와 동기화 폴더 밖에 로컬 `reels-workspace`를 지정하세요. Codex가 `input`, `output`, `projects`를 준비할 수 있습니다. `input`에 사용할 영상 3~5개를 준비한 뒤 아래처럼 요청하세요.

> $reels-creator 내 로컬 reels-workspace 경로는 <작업 폴더>야. input의 영상으로 15초 릴스를 만들어줘. 첫 3초는 강하게 후킹하고 기획안부터 보여줘.

원하는 장면과 구간을 알고 있다면 파일명과 타임코드를 함께 적으세요. 승인 후 `output`에서 영상과 표지를, `projects`에서 편집 계획과 개인 프리셋을 확인할 수 있습니다. [로컬 엔진 실행 방법](references/local-engine.md)

공개용 변경을 커밋하기 전에 배포 루트에서 `python scripts/package_release.py --check-index`를 실행하세요. 새 커밋을 푸시하기 전에는 `python scripts/package_release.py --check-commit HEAD`로 실제 커밋의 파일을 검사하세요. 두 명령 모두 배포 목록, 합성 데모 해시, 민감 경로와 자격 증명 패턴을 검사합니다. 여러 커밋을 푸시한다면 공개될 각 커밋에서 실행하세요.
