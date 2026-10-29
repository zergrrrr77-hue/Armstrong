# 잊혀진 대장간 — Godot 4 프로젝트

16비트 에셋(`assets/`)으로 만든 Godot 4.4 프로젝트입니다. 웹으로 내보내서 **아이폰 사파리**에서 플레이하는 것을 목표로 합니다.

## 지금 들어 있는 것 (1단계)

- **첫 지역 "잊혀진 마을 외곽"**: 풀밭, 떠 있는 발판, 물웅덩이(빠지면 부활), 돌길, 2칸 높이 절벽. 시차 언덕 배경도 있습니다.
- **주인공**: 이동, 점프(짧게 누르면 낮게), 검 공격(길게 누르면 연속), 피격 깜빡임, 사망 후 시작 지점에서 부활
- **슬라임 7마리**: 가까이 가면 통통 튀며 다가오고, 닿으면 피해를 줍니다. 처치하면 12초 뒤 다시 나타납니다.
- **손맛**: 히트스톱, 화면 흔들림, 대미지 숫자, 10% 확률 치명타
- **모바일 터치**: 왼쪽 아무 곳이나 누르면 생기는 투명 조이스틱, 오른쪽에 반투명 공격·점프 버튼. 여러 손가락을 동시에 쓸 수 있습니다.
- **한글 픽셀 폰트**: 갈무리9 (SIL OFL, `assets/fonts/Galmuri-OFL.md`)

## 조작

| PC | 모바일 | 동작 |
|---|---|---|
| A D / ← → | 왼쪽 화면 드래그 | 이동 |
| W / ↑ / Space | 점프 버튼 | 점프 |
| J / Z | 공격 버튼 | 검 공격 (길게 누르면 연속) |

## 실행 · 내보내기

1. [Godot 4.4](https://godotengine.org/download)(표준판, .NET 아님)를 설치하고 이 폴더(`project.godot`)를 엽니다.
2. F5로 실행합니다.
3. 웹으로 내보내기: **프로젝트 → 내보내기 → Web**을 선택합니다. 처음이면 "내보내기 템플릿 관리"에서 템플릿을 내려받은 뒤 **프로젝트 내보내기**를 누릅니다. 결과물은 `../build/web/`에 생깁니다.
   - 명령줄로 하려면: `godot --headless --path forgotten-forge/godot --export-release "Web" ../build/web/index.html`
4. `build/web` 폴더를 웹에 올리면 아이폰 사파리에서 링크로 플레이할 수 있습니다. 예: itch.io에 HTML 게임으로 zip 업로드, 또는 Netlify. 단일 스레드 내보내기라 특별한 서버 헤더가 필요 없습니다.

## 구조

```
project.godot          480×270 픽셀 화면, 비율 확장, Nearest 필터, Compatibility 렌더러(웹 필수)
scenes/main.tscn       지역 루트 (scripts/main.gd가 지형·장식·적·UI를 코드로 조립)
scenes/player.tscn     주인공 (CharacterBody2D + AnimatedSprite2D + 검 판정 Area2D + 카메라)
scenes/slime.tscn      슬라임
scripts/game.gd        오토로드: 키 입력 등록, 히트스톱, 화면 흔들림, 대미지 숫자
scripts/main.gd        지형 칠하기 → 이웃을 보고 타일 자동 선택(모서리·옆면·물가·절벽) → 배치
scripts/touch_controls.gd  투명 조이스틱 + 버튼 (터치 기기에서만 보임)
scripts/hud.gd         체력 바, 지역 이름, 세로 화면일 때 "가로로 돌려 주세요"
tests/combat_test.gd   헤드리스 전투 테스트
```

## 테스트

```
godot --headless --path forgotten-forge/godot -s res://tests/combat_test.gd
```

주인공이 슬라임에게 다가가 공격해 처치하고, 다른 슬라임에 닿으면 체력이 줄어드는지 확인합니다. 마지막 줄에 `PASS`가 나오면 통과입니다.
