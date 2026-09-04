class_name ChaseCamera
extends Camera3D

## 우주선을 부드럽게 따라가는 3인칭 카메라.
## 우주선에 그대로 붙이면 움직임이 딱딱한데, 위치와 회전을 살짝 지연시키면
## 선회할 때 기체가 화면 안에서 흐르듯 움직여 훨씬 영화 같아집니다.

var target: Node3D
var offset := Vector3(-0.75, 2.05, 7.0)
var look_ahead := 13.0
## 시선을 기체보다 조금 위로 두면 우주선이 화면 아래쪽에 앉아
## 정면의 행성을 가리지 않습니다.
var look_up := 1.35
var position_smooth := 5.0
var rotation_smooth := 7.0

func _ready() -> void:
	# 첫 프레임에 카메라가 날아오지 않도록 목표 위치에 바로 붙입니다.
	if target != null:
		global_transform = _desired_transform()

func _physics_process(delta: float) -> void:
	if target == null:
		return

	var desired := _desired_transform()

	var pos_t: float = 1.0 - exp(-position_smooth * delta)
	var rot_t: float = 1.0 - exp(-rotation_smooth * delta)

	var new_origin := global_position.lerp(desired.origin, pos_t)
	var current_q := global_transform.basis.get_rotation_quaternion()
	var desired_q := desired.basis.get_rotation_quaternion()
	var new_basis := Basis(current_q.slerp(desired_q, rot_t))

	global_transform = Transform3D(new_basis, new_origin)

func _desired_transform() -> Transform3D:
	var t := target.global_transform
	var origin: Vector3 = t * offset
	# 기체보다 조금 앞을 바라봐야 진행 방향이 화면에 들어옵니다.
	var look_at_point: Vector3 = t.origin + t.basis * Vector3(0.0, look_up, -look_ahead)

	var dir := look_at_point - origin
	if dir.length_squared() < 0.0001:
		return Transform3D(global_transform.basis, origin)

	var up := t.basis.y
	# 시선과 업벡터가 거의 나란하면 look_at 이 실패하므로 세계 상방으로 대체합니다.
	if abs(dir.normalized().dot(up.normalized())) > 0.999:
		up = Vector3.UP

	return Transform3D(Basis.IDENTITY, origin).looking_at(look_at_point, up)
