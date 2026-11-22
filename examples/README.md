# 로컬 샘플 프로젝트

실제 사람이나 사진을 포함하지 않는 테스트용 도형 PNG 3장을 생성합니다. 생성 폴더를 아래 자동 모드에 입력하면 편집 계획 JSON과 영상·표지가 만들어집니다.

```text
python examples/make_sample.py "<샘플 미디어 폴더>"
python scripts/reel_engine.py auto "<샘플 미디어 폴더>" --project-id sample-reel --title "작은 장면들" --seconds 6 --output "<결과 폴더>"
```

Windows는 `py -3`, macOS는 `python3`를 사용할 수 있습니다. 최종 영상에는 사용 권한이 있는 실사 사진이나 영상 프레임을 사용하세요.

`personal-style.json`은 개인 프리셋 샘플입니다. `save-style my-style examples/personal-style.json`으로 등록하고 계획을 만들 때 `--personal-style my-style`을 사용하세요.
