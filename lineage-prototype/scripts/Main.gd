extends Node2D

## 1단계 뼈대: 격자 바닥을 그리고 플레이어와 카메라를 생성한다.
## Armstrong의 PlanetSurface.gd와 같은 방식으로, 씬 파일은 빈 루트만 두고
## 실제 구성은 여기 _ready()에서 코드로 조립한다.

const GRID_SIZE := 64.0
const GRID_EXTENT := 20 # 격자 칸 개수 (중심에서 한 방향으로)
const BG_COLOR := Color(0.07, 0.06, 0.09)
const GRID_COLOR := Color(0.18, 0.16, 0.22)

var player: CharacterBody2D

func _ready() -> void:
	player = preload("res://scripts/Player.gd").new()
	player.name = "Player"
	add_child(player)

	var camera := Camera2D.new()
	camera.zoom = Vector2(1.5, 1.5)
	camera.position_smoothing_enabled = true
	camera.position_smoothing_speed = 8.0
	player.add_child(camera)
	camera.make_current()

func _draw() -> void:
	var half_extent := GRID_EXTENT * GRID_SIZE
	draw_rect(Rect2(Vector2(-half_extent, -half_extent), Vector2(half_extent, half_extent) * 2.0), BG_COLOR)
	for i in range(-GRID_EXTENT, GRID_EXTENT + 1):
		var offset := i * GRID_SIZE
		draw_line(Vector2(offset, -half_extent), Vector2(offset, half_extent), GRID_COLOR)
		draw_line(Vector2(-half_extent, offset), Vector2(half_extent, offset), GRID_COLOR)
