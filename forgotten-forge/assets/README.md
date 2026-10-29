# 《잊혀진 대장간》 16비트 에셋 팩

`tools/make_assets.py`가 모든 픽셀을 코드로 찍어 만든 에셋입니다. 안티앨리어싱·흐림·그라데이션 없이 공용 팔레트(`palette/`) 색만 씁니다. 색이나 포즈를 바꾸려면 스크립트를 고치고 `python3 forgotten-forge/tools/make_assets.py`를 다시 실행하면 전부 같은 규격으로 새로 뽑힙니다.

## Godot 4에 넣기

1. 이 `assets` 폴더를 Godot 프로젝트 루트에 그대로 복사합니다 → 경로가 `res://assets/...`가 됩니다.
2. **프로젝트 설정 → 렌더링 → 텍스처 → 기본 텍스처 필터 = Nearest** (픽셀이 흐려지지 않게).
3. 바로 쓰는 리소스
   - `godot/player_frames.tres`, `godot/slime_frames.tres` → `AnimatedSprite2D`의 Sprite Frames에 지정
   - `godot/forest_tileset.tres` → `TileMapLayer`의 Tile Set에 지정 (충돌 포함, 발판은 아래에서 통과)

## 캐릭터 · 몬스터 (프레임 32×32, 왼쪽 → 오른쪽, 발바닥 y=30)

| 파일 | 프레임 | 재생 | 내용 |
|---|---|---|---|
| `characters/player_idle.png` | 4 | 6fps 반복 | 숨쉬기, 망토 흔들림 |
| `characters/player_walk.png` | 6 | 10fps 반복 | 다리 교차, 상체 흔들림 |
| `characters/player_attack.png` | 6 | 14fps 1회 | 머리 뒤로 치켜듦 → 내려베기(잔상) → 마무리 → 복귀 |
| `characters/player_hurt.png` | 3 | 10fps 1회 | 움찔 → 흰색 섬광 → 회복 |
| `characters/player_death.png` | 4 | 8fps 1회 | 비틀 → 무릎 → 쓰러짐 → 누움(검 떨어짐) |
| `monsters/slime_idle.png` | 4 | 6fps 반복 | 출렁임 |
| `monsters/slime_move.png` | 6 | 10fps 반복 | 압축 → 늘어나며 점프 → 공중 → 착지 압축 |
| `monsters/slime_attack.png` | 4 | 10fps 1회 | 화난 눈 웅크림 → 입 벌리고 돌진 → 복귀 |
| `monsters/slime_hurt.png` | 3 | 10fps 1회 | X눈 찌그러짐 → 흰색 섬광 → 출렁 회복 |
| `monsters/slime_death.png` | 4 | 8fps 1회 | 녹아내림 → 물방울 튀며 웅덩이 |

캐릭터는 오른쪽을 바라봅니다. 왼쪽은 `flip_h = true`로 뒤집어 씁니다.

## 검 아이콘 (32×32) — 형태 고정, 색 슬롯만 교체

모든 검은 **같은 실루엣**을 씁니다. 왼쪽 아래 폼멜 → 손잡이 4칸 → 칼날과 직각인 가드 7칸 → 16칸 대각선 칼날이고, 칼날은 위쪽 날 / 몸통 / 그림자의 3줄입니다. 등급마다 아래 색 슬롯만 바꾸고, 고유 장식은 칼날 바깥 1~2px 안에서만 추가합니다.

| 파일 | 등급 | 날(밝은 면) | 칼날 몸통 | 그림자 | 홈(풀러) | 가드 | 손잡이 감기 | 보석 | 고유 장식 |
|---|---|---|---|---|---|---|---|---|---|
| `items/sword_rusty.png` 낡은 검 | 일반 | mt1 | mt2 | mt3 | 없음 | 쇠 mt3/mt4 | 가죽 lt1/lt2 | 없음 | 녹 얼룩, 이 빠진 날 |
| `items/sword_hunter.png` 숲 사냥꾼의 검 | 고급 | mt0 | mt1 | mt2 | mt2 | 청동 gd1/gd2 | 초록 가죽 gr3/gr4 | 초록 gr2 | 가드 끝 말림 |
| `items/sword_moonlight.png` 달빛 검 | 희귀 | mo0 | mo1 | mo2 | 파랑 mo3 | 은 mt0/mt2 | 남색 bl3/bl4 | 파랑 mo3 | 초승달 가드, 반짝임 |
| `items/sword_ember.png` 꺼지지 않는 불씨 | 전설 | fi0 | fi1 | fi2 | fi3 | 금 gd1/gd2 | 검정+금 lt3/gd2 | 빨강 rd1 | 불꽃 혀, 떠다니는 불티 |

캐릭터가 손에 쥔 검(`hand_sword`)도 같은 색 규칙(`SWORD_RULES`)을 씁니다.

## 숲 타일셋 `tiles/forest_tileset.png` (32×32, 8열 × 6행, 측면 시점)

풀 지면 윗면은 타일 위에서 3px 아래(y=3)에 있고, 그 위 0~2행에는 풀잎이 솟습니다. 장식 타일은 지면 타일 바로 위 칸에 놓습니다.

| 행 \ 열 | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|---|
| **0** | 풀 윗면·왼끝 | 풀 윗면 | 풀 윗면·오른끝 | 풀 윗면·한 칸 | 흙 속 | 흙 속(자갈) | 흙 옆면·왼쪽 | 흙 옆면·오른쪽 |
| **1** | 아랫면·왼쪽 | 아랫면 | 아랫면·오른쪽 | 아랫면·한 칸 | 한 칸 기둥 | 풀→흙길 경계 | 흙길→풀 경계 | 흙길 윗면 |
| **2** | 발판·왼쪽 | 발판·가운데 | 발판·오른쪽 | 발판·한 칸 | 돌길 윗면 | 돌길·왼끝 | 돌길·오른끝 | 돌벽돌 |
| **3** | 절벽 윗면·왼쪽 | 절벽 윗면 | 절벽 윗면·오른쪽 | 절벽 암벽 | 절벽 옆면·왼쪽 | 절벽 옆면·오른쪽 | 절벽 아래 돌무더기 | 절벽 암벽(균열) |
| **4** | 수면 프레임1 | 수면 프레임2 | 물 속 | 깊은 물 | 물가(오른쪽이 물) | 물가(왼쪽이 물) | 흙 속(뿌리) | 흙 속(묻힌 바위) |
| **5** | 장식·풀 덤불 | 장식·키 큰 풀 | 장식·꽃(분홍·노랑) | 장식·꽃(흰·보라) | 장식·작은 돌 | 장식·덤불 | 장식·버섯 | 장식·고사리 |

- 수면 프레임 1·2를 번갈아 쓰면 물결이 움직입니다(TileSet 아틀라스 애니메이션으로 지정 가능).
- 흙 속·암벽 텍스처는 좌표 기반 노이즈라 같은 타일을 반복해도 이음새가 보이지 않습니다.
- 충돌: 지면·절벽·돌길은 윗면부터 막힘, 발판은 한쪽 통과(one-way), 물·장식은 충돌 없음.
- 조립 예시: `../assets-preview/tileset_demo.png`

## 오브젝트 (투명 배경, 바닥선 = 이미지 맨 아래)

| 파일 | 크기 | 내용 |
|---|---|---|
| `objects/tree_oak.png` | 64×96 | 둥근 활엽수 (4단 명암 잎, 뿌리 퍼짐) |
| `objects/tree_pine.png` | 48×96 | 침엽수 5단 |
| `objects/stump.png` | 32×32 | 나이테 그루터기 + 이끼·버섯 |
| `objects/log_fallen.png` | 64×32 | 쓰러진 통나무 (부러진 끝, 이끼) |
| `objects/rock_small.png` / `rock_large.png` | 32×32 / 64×48 | 바위 (큰 바위는 이끼) |
| `objects/flowers.png` | 32×32 | 꽃과 풀 무더기 |
| `objects/fence_mid.png` / `fence_end.png` / `fence_broken.png` | 32×32 | 낡은 나무 울타리 (가운데 칸은 가로로 이어 붙임) |

## 팔레트

`palette/forgotten_forge.gpl` (Aseprite·GIMP에서 불러오기) · `palette/forgotten_forge_palette.png`. 새 에셋도 이 팔레트 안에서 그리면 스타일이 유지됩니다.
