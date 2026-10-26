# 같은 화면의 글씨를 목차로 이동시키기

## 지켜야 할 동작

1. 시작 화면에서 로드맵의 원래 글씨가 보인다.
2. 그 화면에서 한 번 클릭하면 바로 그 개체가 1.2초 동안 이동·축소된다.
3. 글씨가 목차 위치에 도착한 뒤 아래 본문 또는 사진을 공개한다.
4. 다음 클릭은 다음 논리 슬라이드로 이동한다. 같은 사진을 다시 보여 주는 정적 중간 장을 끼우지 않는다.

빈 다음 화면에서 새 글씨를 올리는 entrance 애니메이션, 화면 전체를 움직이는 전환, 사라진 뒤 새 글씨로 바뀌는 효과는 이 동작이 아니다.

## 구현 근거

- `bs-focus`: 시작 화면의 실제 편집 가능한 텍스트 개체. `animMotion`과 `animScale`은 모두 이 개체의 현재 ID를 대상으로 한다.
- `bs-anchor`: 상단 목적지의 실제 박스. 이동량은 두 중심 좌표의 차이를 슬라이드 크기로 나눈 값이다. 축소 비율은 목적지 글씨 크기 / 출발 글씨 크기다.
- `bs-reveal-*`: 뒤에서 공개할 내용. 검은 `bs-mask` 아래에 미리 배치한다.
- `bs-exit-*`: 로드맵의 나머지 개체. 이동과 함께 사라지되 `bs-focus`에는 등장·퇴장 효과를 넣지 않는다.
- 타임라인의 주 시퀀스는 현재 슬라이드의 클릭을 기다린다. 사진 공개까지 같은 클릭의 묶음으로 처리한다.
- 정적 원본에서는 같은 글씨의 좌표·크기만 목적지로 맞추고 덮개·로드맵 개체·타임라인을 제거한다. 논리 슬라이드 수는 동일하다.

스크립트는 PptxGenJS로 만든 초안의 슬라이드 XML만 패치한다. 관계 파일·미디어·노트 등 나머지 ZIP 파트가 바뀌지 않았는지 확인한다. 임의의 타사 PPTX에 이 패치를 적용하지 않는다.

## 수정 뒤 회귀 확인

| 변경 | 확인할 것 |
| --- | --- |
| 목차 문구 변경 | 출발 글씨와 목적지의 표기가 정확히 같고, 대상 ID가 실제 개체를 가리키는가 |
| 목차 순서 변경 | 목적지 중심 좌표를 다시 계산했는가 |
| 슬라이드 추가·삭제 | 효과가 고정된 ‘몇 번 슬라이드’가 아니라 실제 로드맵에 붙어 있는가 |
| 사진 추가·교체 | 원본 비율·라벨·테두리가 유지되고 같은 클릭에 공개되는가 |
| PDF 생성 | 완료 상태이며 중복 페이지·검은 덮개가 없는가 |
| 폰트 변경 | 실제 폰트로 잘림을 검사했고, 재생 PC에서도 같은 폰트를 쓸 수 있는가 |

`npm test`는 개체 동일성·경로 계산·순서 변경·정적 결과·관계 연결을 검사한다. 실제 PowerPoint의 동작·발표 PC 가독성·클릭 타이밍은 별도 실행으로 확인해야 한다.

## 공식 참조

- [PptxGenJS 텍스트](https://gitbrent.github.io/PptxGenJS/docs/api-text/)
- [PptxGenJS 이미지 contain 배치](https://gitbrent.github.io/PptxGenJS/docs/api-images/)
- [Microsoft PresentationML 애니메이션](https://learn.microsoft.com/en-us/office/open-xml/presentation/working-with-animation)
- [Microsoft AnimateScale](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.presentation.animatescale)
