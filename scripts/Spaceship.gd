extends CharacterBody3D

## 자유 비행하는 우주선. W/S 로 전후진, A/D 로 방향 전환.
## 우주라 중력이 없으므로 floating 모드를 쓰고, 추력이 없으면 서서히 감속합니다.

const THRUST_ACCEL := 16.0
const MAX_SPEED := 26.0
const TURN_SPEED := 1.6
const DAMPING := 1.8
const BANK_ANGLE := 0.42

var _model: Node3D
var _bank := 0.0

func _ready() -> void:
	motion_mode = CharacterBody3D.MOTION_MODE_FLOATING
	_model = get_node_or_null("StarshipModel")

func _physics_process(delta: float) -> void:
	var turn_input := 0.0
	if Input.is_physical_key_pressed(KEY_A):
		turn_input += 1.0
	if Input.is_physical_key_pressed(KEY_D):
		turn_input -= 1.0
	rotate_y(turn_input * TURN_SPEED * delta)

	var thrust_input := 0.0
	if Input.is_physical_key_pressed(KEY_W):
		thrust_input += 1.0
	if Input.is_physical_key_pressed(KEY_S):
		thrust_input -= 1.0

	var forward := -global_transform.basis.z
	if thrust_input != 0.0:
		velocity = velocity.move_toward(forward * thrust_input * MAX_SPEED, THRUST_ACCEL * delta)
	else:
		velocity = velocity.move_toward(Vector3.ZERO, DAMPING * delta)

	move_and_slide()

	_update_model(turn_input, thrust_input, delta)

func _update_model(turn_input: float, thrust_input: float, delta: float) -> void:
	if _model == null:
		return

	# 선회할 때 기체를 살짝 기울입니다. 비행기처럼 보이게 하는 작은 차이입니다.
	var t: float = clamp(delta * 4.0, 0.0, 1.0)
	_bank = lerp(_bank, -turn_input * BANK_ANGLE, t)
	_model.rotation.z = _bank

	# 전진할 때만 엔진에 불이 붙습니다.
	StarshipBuilder.set_thrust(_model, max(thrust_input, 0.0), delta)
