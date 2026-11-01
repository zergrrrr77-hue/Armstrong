# Armstrong — 우주여행 게임 (1단계 프로토타입)

`DESIGN.md`의 1단계 기획서를 구현한 Godot 4.x 프로젝트입니다. "이동 → 착륙 → 탐험 → 채집"의 핵심 루프 하나를 검증하는 최소 프로토타입입니다.

## 실행 방법

1. [Godot 4.x](https://godotengine.org/download) (4.2 이상 권장)를 설치합니다.
2. Godot 프로젝트 매니저에서 이 저장소 폴더(`project.godot`)를 엽니다.
3. F5(또는 상단의 실행 버튼)로 실행합니다. 기본 씬은 `scenes/Main.tscn`(우주 씬)입니다.

## 조작 방법

| 상황 | 입력 | 동작 |
|---|---|---|
| 우주선 조종 | W / S | 전진 / 후진 |
| 우주선 조종 | A / D | 좌/우 방향 전환 (기체가 살짝 기울며 선회) |
| 행성 착륙 | E (행성 근처 접근 시) | 착륙 → 행성 표면 씬으로 전환 |
| 도보 이동 | W A S D | 캐릭터 이동 |
| 자원 채집 | E (자원 근처 접근 시) | 자원 획득, 인벤토리에 반영 |
| 이륙 | E (착륙 지점 근처 접근 시) | 우주 씬으로 복귀 |

화면 좌상단에 현재 씬의 조작 안내, 우상단에 인벤토리, 하단 중앙에 상호작용 가능할 때의 프롬프트가 표시됩니다.

## 프로젝트 구조

```
project.godot            엔진 설정, 오토로드(GameState/Inventory/HUD) 등록
autoload/
  GameState.gd            현재 착륙한 행성, 행성/자원 데이터 정의
  Inventory.gd             수집한 자원 카운트 + 변경 시그널
scenes/
  Main.tscn                우주 씬 (루트 노드 + 스크립트)
  PlanetSurface.tscn        행성 표면 템플릿 씬 (모든 행성이 공유)
  UI/HUD.tscn                상시 표시되는 UI 오버레이 (오토로드 씬)
scripts/
  Main.gd                   태양/행성/우주선을 런타임에 생성
  PlanetSurface.gd           지형/언덕/착륙장/자원/플레이어를 런타임에 생성
  Spaceship.gd                우주선 이동 로직
  Player.gd                   도보 이동 + 상호작용(E) 로직
  LandingZone.gd               행성 근접 시 착륙 트리거
  LaunchPad.gd                  행성 표면에서 이륙 트리거
  ResourceNode.gd                채집 가능한 자원 오브젝트
  HUD.gd                          UI 갱신 로직
  ChaseCamera.gd                   우주선을 부드럽게 따라가는 3인칭 카메라
  visuals/
    SpaceVisuals.gd                 별하늘 환경 / 항성 / 행성을 조립
    StarshipBuilder.gd               스타십형 우주선 모델 생성
    MeshLab.gd                        회전체·각기둥 메시 생성 도구
    Spinner.gd                         행성 자전
shaders/
  lib/noise.gdshaderinc            공용 노이즈 라이브러리 (모든 셰이더가 참조)
  space_sky.gdshader                별 + 은하수 + 성운 + 행성 대기
  planet_surface.gdshader            행성 표면 (지구형/화성형/얼음/화산)
  planet_atmosphere.gdshader          대기 테두리
  planet_clouds.gdshader               구름층
  planet_ground.gdshader                지표면 씬의 땅
  star_surface.gdshader                  항성 표면
  star_corona.gdshader                    항성 코로나
  ship_hull.gdshader                       스테인리스강 선체 + 내열 타일
  engine_plume.gdshader                     엔진 화염
assets/
  fonts/NanumGothic-Regular.ttf   한글 UI 렌더링용 폰트 (SIL OFL 1.1, assets/fonts/OFL.txt 참고)
```

## 비주얼이 만들어지는 방식

이미지 텍스처나 3D 모델 파일을 전혀 쓰지 않습니다. 별, 대륙, 구름, 용암, 우주선 선체까지
전부 **코드와 셰이더로 그려집니다.** 덕분에 저장소가 가볍고, 값 하나만 바꿔도 행성이 달라집니다.

- **별하늘** — 별을 오브젝트로 만들지 않고 시선 방향만으로 계산합니다. 사실상 무한한 개수의
  별을 거의 공짜로 그리며, 은하수 띠 쪽에 별이 촘촘히 몰리도록 밀도를 조절합니다.
- **행성** — 3D 노이즈로 고도를 만들고, 그 값으로 바다/육지/설선을 나눕니다. 지구형에는
  밤이 된 쪽에만 도시 불빛이 켜지고, 화성형에는 적도를 따라 대협곡이 지나갑니다.
- **대기** — 행성보다 살짝 큰 껍질 구에 프레넬(가장자리일수록 밝아짐)을 입혀 만듭니다.
  우주에서 본 지구가 아름다운 가장 큰 이유가 이 얇고 푸른 테두리입니다.
- **우주선** — 프로필 곡선을 회전시켜(선반 깎기) 오자이브 노즈콘과 동체를 만들고,
  스테인리스강 용접 링과 검은 내열 타일을 셰이더로 그립니다.

행성을 추가하거나 색·대기·구름을 바꾸려면 `autoload/GameState.gd` 의 `planets` 배열만
수정하면 됩니다. 셰이더를 건드릴 필요가 없습니다.

### 다른 프로젝트로 옮겨 쓰기

비주얼 부분은 게임 로직과 분리되어 있습니다. 다른 Godot 4 프로젝트에 그대로 쓰려면
`shaders/` 폴더 전체와 `scripts/visuals/` 폴더를 복사한 뒤 이렇게 호출하면 됩니다.

```gdscript
add_child(SpaceVisuals.create_environment())        # 별하늘 + 블룸
add_child(SpaceVisuals.create_star(6.0))            # 태양
add_child(SpaceVisuals.create_planet_visual(data))  # 행성 (data 형식은 GameState.gd 참고)
add_child(StarshipBuilder.create())                 # 우주선 모델
```

UI 텍스트(조작 안내, 인벤토리, 상호작용 프롬프트)는 한글로 표시됩니다. Godot의 기본 내장 폰트는 한글 글리프를 포함하지 않으므로, `project.godot`의 `gui/theme/custom_font` 설정으로 `assets/fonts/NanumGothic-Regular.ttf`를 프로젝트 기본 폰트로 지정해 두었습니다.

씬 파일(.tscn)은 스크립트만 붙은 최소 루트 노드로 두고, 실제 지오메트리(태양·행성·지형·자원·우주선·플레이어)는 각 스크립트의 `_ready()`에서 코드로 생성합니다. 행성이나 자원을 추가/수정하려면 `autoload/GameState.gd`의 `planets` 배열만 바꾸면 됩니다.

## 1단계 완료 기준 충족 여부

- [x] 우주선으로 임의의 행성까지 이동해 착륙할 수 있다
- [x] 착륙한 행성 표면을 걸어다닐 수 있다
- [x] 최소 1종 이상의 자원을 채집할 수 있다
- [x] 인벤토리에 채집 결과가 반영되어 화면에 보인다

자세한 기획 내용과 백로그는 `DESIGN.md`를 참고하세요.

---

# 잊혀진 대장간 — 리니지풍 쿼터뷰 RPG (웹, v1.0)

`forgotten-forge/index.html`을 브라우저로 열면 바로 실행됩니다. 그림·소리는 `forgotten-forge/lineage-assets/`를 상대 경로로 불러옵니다.

- **흐름**: 클래스 선택(기사·요정·마법사) → 마을 외곽 필드 사냥 → 남동쪽 지하 계단 → 던전 → 보스 **몰락한 왕**
- **전투**: 클릭/WASD 이동(장애물은 옆으로 비켜 돌아감), 몬스터 클릭·Space로 공격, 1~4 스킬(클래스별 4종, MP·재사용 대기), Q/E 물약
- **자동사냥(H)**: 가까운 몬스터 공격, 사거리에 맞춰 스킬 사용, 체력 40%·마나 25% 아래에서 물약, 떨어진 아이템 줍기. 직접 조작하면 잠시 멈춤
- **보스**: 체력 절반 이하에서 분노. 전용 스킬 *암흑 베기*(앞으로 날아가는 충격파), *지옥불 강타*(예고 원 뒤 범위 폭발)
- **성장**: 경험치·레벨, 드롭(골드·물약·강화 주문서·보석·등급별 무기/갑옷 5등급), 가방에서 비교·착용·판매
- **강화**: 무기 +6·갑옷 +4까지 안전, 이후 단계별 성공 확률(무기 50→20%, 갑옷 60→20%), 실패 시 +0. 가방에서 몬스터별 드롭률·강화 확률 표 확인
- **연출**: 8방향 프리렌더 스프라이트, 가산 혼합 스킬 이펙트, 던전 횃불 조명, 미니맵, 합성 효과음·환경음·배경음악
- **점검**: `node forgotten-forge/tests/iso_smoke.js [스크린샷 폴더]` — 3클래스 이동·공격·스킬·물약·강화·장비·자동사냥, 던전 입장, 보스 스킬·처치, 휴대폰 정보창 겹침, 오류 0건

## 리니지풍 에셋 생성기

`python3 forgotten-forge/tools/lineage/build.py` (4코어 약 10분) — 3D 형태를 SDF로 조립해 30° 쿼터뷰 도트로 굽습니다.
결과는 `forgotten-forge/lineage-assets/`(시트·`meta.json`·갤러리 `gallery.html`)와 게임 `forgotten-forge/index.html`로 나옵니다.

| 분류 | 내용 |
|---|---|
| 캐릭터 | 기사·요정·마법사 — 8방향 × 대기 6·걷기 8·공격 8·피격 3·사망 6 + 스킬 4종 |
| 몬스터 | 다이어울프·거대 거미·늪 점액·오크 전사·해골 병사·몰락한 왕(스킬 2종) |
| 이펙트 | 스킬 14종, under/over(가산)·solid(일반) 층, 화살·운석 등은 8방향별 |
| 필드 | 지면 타일 9종 × 4변형, 소품 47종(자연·성채·마을·묘지·던전·마을 생활) |
| 아이템 | 아이콘 39종, 등급 테두리 5종, 강화 발광 +7~+10 |
| 사운드 | `lineage-assets/audio/sfx.js` — 효과음·몬스터 음성·스킬음·발소리, 환경음 4종, 배경음악 |
