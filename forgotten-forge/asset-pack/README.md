# 잊혀진 대장간 에셋 팩 (v0.7)

리니지풍 **쿼터뷰(2:1 아이소메트릭) 프리렌더 도트** 에셋 모음입니다. 「잊혀진 대장간」을 만들면서 직접 생성한 그림·이펙트·효과음을 새 프로젝트에서 바로 쓸 수 있게 정리했습니다.

먼저 `previews/_catalog_*.png` 다섯 장을 열어 무엇이 있는지 훑어보세요.

## 들어 있는 것
| 폴더 | 내용 | 형식 |
|---|---|---|
| `characters/` | 기사·요정·마법사 3종 × 8방향 × 9동작(대기·걷기·공격·피격·사망·스킬 4) | `strips/이름_동작_방향.png`(가로 띠) + `frames/동작/방향/00.png`(낱장) + `이름.json` |
| `monsters/` | 고블린·다이어울프·늪 점액·거대 거미·해골 병사·해골 궁수·오크 전사·몰락한 왕(보스)·피의 군주·리치 군주(월드보스, 1.5배 해상도) | 위와 같음 |
| `effects/` | 스킬 이펙트 16종(회전 베기·운석 낙하·지옥불 등) | 층(under/over/solid) × 방향별 가로 띠 + `effects.json` |
| `props/` | 오브젝트 50종: 나무·바위·성벽·탑·집·우물·노점·대장간 화로·던전 벽·보물상자·제단·관·신전·화로의 신·웨이포인트 등 | 낱개 PNG(움직이는 것은 `_0~_3`) + `props.json`(기준점) |
| `tiles/` | 바닥 9종(풀밭·흙길·돌길·늪지·설원·던전·젖은 던전·나무 마루·물) × 변형 4 | 64×32 마름모 + `tiles.json` |
| `items/` | 아이템 아이콘 39종(무기·방어구·장신구·물약·주문서·기타) | 32×32 + `x2/` 64×64 + `items.json` |
| `ui/` | 등급 테두리 5종(일반~전설), 강화 단계별 무기 아이콘(+0·+7·+8·+9·+10) | PNG + `ui.json` |
| `sounds/` | 효과음 56종 × 변형(A=기본, B·C) = 137개 | WAV 44.1kHz 스테레오 + `sounds.json` |
| `music/` | 필드 배경음악 1곡 | MP3 |
| `sheets/` | 원본 스프라이트 시트 전부 + `meta.json`(게임에서 쓰던 그대로) | PNG |
| `previews/` | 한눈에 보는 카탈로그 이미지 | PNG |
| `sounds_engine_sfx.js` | 합성 사운드 엔진(효과음 + 실시간 작곡 배경음악 9곡 + 환경음 4종) | JS |

## 꼭 알아야 할 규칙
- **방향 8개:** `S, SE, E, NE, N, NW, W, SW`(화면 기준 남쪽부터 시계 방향). 좌우 반전 없이 8방향 모두 그려져 있습니다.
- **기준점(anchor):** 캐릭터·몬스터·소품 모두 **발밑(바닥 접점)**입니다. 화면 좌표 `(x, y)`에 세우려면 `drawImage(img, x - anchor_x, y - anchor_y)`로 그립니다.
- **타일:** 64×32 마름모입니다. 타일 (i, j)의 화면 위치는 `((i - j) × 32, (i + j) × 16)`입니다.
- **재생 속도:** 동작은 10fps 기준이고, 걷기는 1.15배 빠르게 재생하면 자연스럽습니다.
- **이펙트:** `under` 층은 캐릭터 뒤에, `over` 층은 앞에 **가산 혼합**(Canvas `lighter`, Unity Additive, Godot Add)으로 그립니다. `solid` 층은 일반 혼합입니다.
- **픽셀아트:** 확대할 때는 반드시 '가장 가까운 픽셀'로 확대합니다.
  - CSS: `image-rendering: pixelated`
  - Godot: Filter → Nearest
  - Unity: Filter Mode → Point

## 엔진별로 바로 쓰기
- **웹(Canvas):** `strips/` 띠를 불러와 `(프레임 번호 × frame_w, 0)`을 잘라 그립니다. JSON의 `anchor_x/anchor_y`를 그대로 씁니다.
- **Godot 4:**
  1. `SpriteFrames`에 동작_방향마다 애니메이션을 만듭니다.
  2. `frames/동작/방향/*.png`를 끌어다 놓습니다.
  3. 스프라이트의 `offset`을 `(frame_w/2 - anchor_x, frame_h/2 - anchor_y)`의 음수로 맞춥니다.
- **Unity:**
  1. 띠를 Sprite Mode = Multiple로 놓고 Grid By Cell Size(frame_w × frame_h)로 자릅니다.
  2. Pivot을 Custom `(anchor_x / frame_w, 1 - anchor_y / frame_h)`로 설정합니다.
- **Phaser:** `this.load.spritesheet(key, strip, { frameWidth, frameHeight })` 후 `setOrigin(anchor_x / frame_w, anchor_y / frame_h)`

## 출처·권리
- 그림·이펙트·효과음은 모두 이 프로젝트에서 직접 만든 것입니다. Python SDF 프리렌더 도구로 생성했고, 효과음은 Web Audio로 합성했습니다. 외부 그림이나 녹음 샘플은 쓰지 않았으므로 자유롭게 쓰고 고칠 수 있습니다.
- `music/field_orch.mp3`는 FluidR3 GM 사운드폰트(CC-BY 3.0)로 렌더링한 곡입니다. 공개 배포할 때는 크레딧에 "FluidR3 GM SoundFont (CC-BY 3.0)"를 표기하세요.
- 더 만들거나 크기·색을 바꾸려면 원본 저장소의 `forgotten-forge/tools/lineage/`(build.py · add_assets.py · worlds.py)를 쓰면 같은 화풍으로 계속 생성할 수 있습니다.
