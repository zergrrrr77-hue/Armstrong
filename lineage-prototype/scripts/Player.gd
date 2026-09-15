extends CharacterBody2D

## 1단계 플레이어: WASD 8방향 이동만 담당한다.
## 이미지 에셋 없이 _draw()로 원판을 그린다 (전투/스탯은 다음 단계에서 추가).

const SPEED := 220.0
const RADIUS := 14.0
const BODY_COLOR := Color(0.85, 0.75, 0.35)
const OUTLINE_COLOR := Color(0.4, 0.32, 0.1)

func _ready() -> void:
	var shape := CollisionShape2D.new()
	var circle := CircleShape2D.new()
	circle.radius = RADIUS
	shape.shape = circle
	add_child(shape)

func _physics_process(_delta: float) -> void:
	var input_dir := Vector2.ZERO
	if Input.is_physical_key_pressed(KEY_W):
		input_dir.y -= 1.0
	if Input.is_physical_key_pressed(KEY_S):
		input_dir.y += 1.0
	if Input.is_physical_key_pressed(KEY_A):
		input_dir.x -= 1.0
	if Input.is_physical_key_pressed(KEY_D):
		input_dir.x += 1.0
	if input_dir.length() > 0.0:
		input_dir = input_dir.normalized()

	velocity = input_dir * SPEED
	move_and_slide()

func _draw() -> void:
	draw_circle(Vector2.ZERO, RADIUS, BODY_COLOR)
	draw_arc(Vector2.ZERO, RADIUS, 0.0, TAU, 32, OUTLINE_COLOR, 2.0)
