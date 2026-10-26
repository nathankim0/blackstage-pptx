# Blackstage PPTX

검은 배경, 큰 굵은 글씨, 짧은 문구로 만드는 발표용 PowerPoint 생성기와 에이전트 스킬입니다. 예제는 일반 프로젝트 브리핑이며, 개인 자료 없이 사용할 수 있습니다.

텍스트·화살표·목차는 편집 가능한 PowerPoint 개체입니다. 로드맵에서 보이던 글씨를 같은 화면에서 상단 목차로 이동·축소하고, 이어서 본문이나 사진을 공개합니다. 단순한 다음 장 등장 효과가 아닙니다.

![예제 PDF 정지 화면 미리보기](docs/preview.png)

## 실행

Node.js 20+와 Python 3.10+가 필요합니다. Python은 표준 라이브러리만 사용합니다.

```bash
git clone https://github.com/nathankim0/blackstage-pptx.git
cd blackstage-pptx
npm ci
npm test
npm run example
```

기본 글꼴은 [Nanum Gothic](https://fonts.google.com/specimen/Nanum+Gothic) Bold입니다. 제작·발표 PC에 설치하거나 JSON의 `font`를 실제 설치된 한글 글꼴로 바꾸세요. 글꼴을 PPTX에 내장하지는 않습니다.

PDF도 만들려면 [LibreOffice](https://www.libreoffice.org/download/download-libreoffice/)를 설치한 뒤 새 출력 이름으로 실행합니다.

```bash
node scripts/build.mjs examples/demo.json output/demo-v2.pptx --pdf
python3 scripts/pptx.py check output/demo-v2.pptx
```

`PYTHON` 환경변수로 Python 실행 파일을 지정할 수 있습니다. 상대 이미지 경로는 실행 폴더가 아니라 입력 JSON 파일 위치를 기준으로 합니다.

PDF 변환은 `fc-match`가 있으면 사용 글꼴을 찾아 임시 LibreOffice 프로필에만 복사합니다. macOS의 headless 변환에서 한글이 사라지는 경우를 피하기 위한 처리이며 시스템 폰트·사용자 프로필은 바꾸지 않습니다. `fc-match`가 없거나 직접 폰트를 지정하려면 `BLACKSTAGE_FONT_DIR`에 사용할 TTF/OTF/TTC 파일이 든 폴더를 지정하세요. macOS에서 폰트를 찾을 수 없으면 변환을 중단합니다.

```bash
BLACKSTAGE_FONT_DIR=/path/to/fonts node scripts/build.mjs examples/demo.json output/demo-v3.pptx --pdf
```

생성 결과:

- `demo-v2.pptx`: 클릭 재생용 원본
- `demo-v2.static.pptx`: 같은 수의 슬라이드로 구성한 애니메이션 완료 상태 원본
- `demo-v2.checks.json`: 경로·배율·구조 검사와 파일 해시. 실제 PowerPoint 재생 확인은 기본값 `false`
- `demo-v2.pdf`: `--pdf`를 썼을 때만 생성되는 정적 배포본

기존 결과물은 덮어쓰지 않습니다. 출력 파일이 이미 있거나 변환이 실패하면 새 결과 세트를 게시하지 않습니다. 생성 임시 폴더는 정리합니다. 입력으로 신뢰할 수 있는 로컬 JSON·이미지를 사용하세요. 임의의 기존 PPTX를 import/export하는 편집기는 아닙니다.

## 입력

[examples/demo.json](examples/demo.json)을 복사해 수정하세요. `sections`는 상단 목차이며 안정적인 `id`와 표시용 `label`을 가집니다. `toc.items`는 별도 목록이어서 상단 목차와 다르게 구성할 수 있습니다.

| kind | 입력 | 용도 |
| --- | --- | --- |
| `cover` | `title`, 선택 `kicker`·`subtitle` | 표지, 상단 목차 없음 |
| `toc` | `items` 1~6개 | 중앙에 묶은 왼쪽 정렬 목록 |
| `title` | `title` | 한 줄 제목, 영상 별도 재생 안내 등 |
| `text` | `title`, `lines` 최대 2줄 | 반복 안내 |
| `image` | `path`, 선택 `alt` | 포스터·사진 한 장, 원본 비율 유지 |
| `gallery` | 선택 `title`, `images` 1~4개 | 큰 라벨·테두리의 2×2 사진 묶음 |
| `roadmap` | `steps` 3개, `focus`, `section`, `reveal` | 원래 글씨를 목차로 옮긴 뒤 본문 공개 |

공통 선택 항목은 `notes`, `section`, `nav:false`입니다. `cover`·`toc`는 자동으로 상단 목차를 숨깁니다. 로드맵은 목적지 목차가 필요하므로 `nav:false`를 받지 않습니다. 상단 목차는 최대 네 항목입니다.

```json
{"kind":"text","section":"prepare","title":"1. 자료 준비",
 "lines":[[{"text":"기간: "},{"date":"2026-11-09"},{"text":"–"},{"date":"2026-11-20"}],"팀별로 진행"]}
```

`date`는 실제 요일을 계산해 노란색으로 표시합니다. 라벨과 시간은 흰색을 유지합니다. 다른 부분까지 노랗게 하려고 날짜를 일반 문자열로 꾸미지 마세요.

```json
{"kind":"gallery","section":"prepare","title":"준비 기록",
 "images":[{"path":"images/day-1.jpg","label":"1일차","alt":"첫날 준비 기록"},
           {"path":"images/day-2.jpg","label":"2일차","alt":"둘째 날 준비 기록"}]}
```

사진은 자르지 않고 넣습니다. 긴 본문은 자동 축소하지 않고 오류로 알립니다. 폭 검사는 보수적인 추정치이며 실제 글꼴 렌더 검수를 대체하지 않습니다. 내용이 길면 슬라이드를 나누세요.

## 에이전트 스킬 설치

저장소 전체가 하나의 스킬입니다. `SKILL.md`만 복사하면 스크립트가 빠지므로 전체 디렉터리를 연결하세요. 아래 명령은 저장소 루트에서 실행하며 같은 이름의 기존 스킬이 있으면 바꾸지 않습니다.

```bash
mkdir -p ~/.codex/skills
ln -s "$PWD" ~/.codex/skills/blackstage-pptx
# Claude Code를 쓴다면 같은 저장소를 연결
mkdir -p ~/.claude/skills
ln -s "$PWD" ~/.claude/skills/blackstage-pptx
```

새 세션에서 `$blackstage-pptx`를 호출하거나 ‘검은 배경에 큰 굵은 글씨로 발표 자료를 만들어줘’라고 요청합니다. 자세한 제작 규칙은 [SKILL.md](SKILL.md), 같은 화면 이동 방식과 회귀 기준은 [references/continuous-motion.md](references/continuous-motion.md)에 있습니다.

## 검증 범위와 한계

- 테스트는 동일 개체의 이동·축소, 실제 중심 좌표와 배율, 목차·슬라이드 순서 변경, 사진 비율, 날짜, 정적 완료 상태, 파일 보존, ZIP 관계를 확인합니다. LibreOffice·Poppler가 있으면 PDF 페이지 수와 나눔 글꼴의 실제 포함도 검사합니다. 없으면 PDF 검사만 건너뜁니다.
- PDF는 완료 상태를 별도 원본에서 내보냅니다. 클릭 재생 원본에 정적 중복 장을 끼워 넣지 않습니다.
- LibreOffice·PDF·구조 검사 통과는 Microsoft PowerPoint의 실제 슬라이드쇼 재생 증명이 아닙니다. 특히 같은 글씨 이동 → 내용 공개 → 다음 클릭의 다음 장을 실제 발표 PC에서 확인하세요. 이 저장소는 PowerPoint 실제 재생 검증을 했다고 주장하지 않습니다.
- PDF 변환에는 LibreOffice를 사용하며 별도 임시 프로필로 실행합니다. 사용자의 열린 LibreOffice 문서를 조작하지 않습니다.
- 내장 발표 테마는 16:9 한 종류입니다. 웹 편집기·동영상 내장·임의의 PPTX 변환 기능은 포함하지 않습니다.

## 라이선스

[MIT](LICENSE). PptxGenJS와 사용자가 선택한 글꼴·사진의 라이선스는 각각 따릅니다. 저장소는 사용자 사진이나 글꼴 파일을 배포하지 않습니다.
