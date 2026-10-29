extends Control
## 모바일 터치 조작: 왼쪽 아무 곳이나 누르면 생기는 투명 조이스틱 + 오른쪽 공격·점프 버튼.
## 버튼은 반투명 원으로 그려 배경에 녹아들게 한다. 멀티터치를 손가락 번호별로 따로 추적한다.

@export var force_visible := false   # 데스크톱에서 마우스로 시험할 때 켠다

const JOY_RADIUS := 34.0
const KNOB_RADIUS := 13.0
const KNOB_TRAVEL := 24.0
const DEADZONE := 7.0

var _touches := {}          # 손가락 번호 -> "joy" | "attack" | "jump"
var _joy_origin := Vector2.ZERO
var _joy_knob := Vector2.ZERO
var _joy_active := false


func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	visible = force_visible or DisplayServer.is_touchscreen_available()
	get_viewport().size_changed.connect(queue_redraw)


func _size() -> Vector2:
	return get_viewport_rect().size


func _attack_center() -> Vector2:
	var s := _size()
	return Vector2(s.x - 52.0, s.y - 58.0)


func _jump_center() -> Vector2:
	var s := _size()
	return Vector2(s.x - 112.0, s.y - 36.0)


func _default_joy() -> Vector2:
	return Vector2(64.0, _size().y - 62.0)


func _input(event: InputEvent) -> void:
	if not visible:
		return
	if event is InputEventScreenTouch:
		if event.pressed:
			_on_touch_down(event.index, event.position)
		else:
			_on_touch_up(event.index)
	elif event is InputEventScreenDrag and _touches.get(event.index) == "joy":
		_move_knob(event.position)


func _on_touch_down(index: int, pos: Vector2) -> void:
	if pos.distance_to(_attack_center()) < 38.0:
		_touches[index] = "attack"
		Input.action_press("attack")
	elif pos.distance_to(_jump_center()) < 30.0:
		_touches[index] = "jump"
		Input.action_press("jump")
	elif pos.x < _size().x * 0.5 and not _joy_active:
		_touches[index] = "joy"
		_joy_active = true
		_joy_origin = pos
		_move_knob(pos)
	queue_redraw()


func _on_touch_up(index: int) -> void:
	var role: String = _touches.get(index, "")
	_touches.erase(index)
	match role:
		"attack":
			Input.action_release("attack")
		"jump":
			Input.action_release("jump")
		"joy":
			_joy_active = false
			_joy_knob = Vector2.ZERO
			Input.action_release("move_left")
			Input.action_release("move_right")
	queue_redraw()


func _move_knob(pos: Vector2) -> void:
	_joy_knob = (pos - _joy_origin).limit_length(KNOB_TRAVEL)
	if _joy_knob.x < -DEADZONE:
		Input.action_press("move_left", clampf(-_joy_knob.x / KNOB_TRAVEL, 0.0, 1.0))
		Input.action_release("move_right")
	elif _joy_knob.x > DEADZONE:
		Input.action_press("move_right", clampf(_joy_knob.x / KNOB_TRAVEL, 0.0, 1.0))
		Input.action_release("move_left")
	else:
		Input.action_release("move_left")
		Input.action_release("move_right")
	queue_redraw()


func _draw() -> void:
	var white := Color(1, 1, 1)
	# 조이스틱: 평소엔 흐린 고리만, 누르면 손가락 자리로 이동
	var c := _joy_origin if _joy_active else _default_joy()
	var a := 0.32 if _joy_active else 0.16
	draw_circle(c, JOY_RADIUS, Color(1, 1, 1, a * 0.25))
	draw_arc(c, JOY_RADIUS, 0.0, TAU, 40, Color(1, 1, 1, a), 1.0)
	draw_circle(c + _joy_knob, KNOB_RADIUS, Color(1, 1, 1, a + 0.08))
	draw_arc(c + _joy_knob, KNOB_RADIUS, 0.0, TAU, 24, Color(1, 1, 1, a + 0.15), 1.0)
	# 공격 버튼: 검 모양
	var ac := _attack_center()
	var on_a := "attack" in _touches.values()
	draw_circle(ac, 30.0, Color(1, 0.85, 0.6, 0.3 if on_a else 0.12))
	draw_arc(ac, 30.0, 0.0, TAU, 40, Color(1, 1, 1, 0.35), 1.0)
	draw_line(ac + Vector2(-8, 8), ac + Vector2(9, -9), Color(white, 0.8), 3.0)
	draw_line(ac + Vector2(-10, 2), ac + Vector2(-2, 10), Color(white, 0.8), 2.0)
	draw_line(ac + Vector2(-9, 9), ac + Vector2(-13, 13), Color(white, 0.8), 2.0)
	# 점프 버튼: 위쪽 화살표
	var jc := _jump_center()
	var on_j := "jump" in _touches.values()
	draw_circle(jc, 22.0, Color(1, 0.85, 0.6, 0.3 if on_j else 0.12))
	draw_arc(jc, 22.0, 0.0, TAU, 32, Color(1, 1, 1, 0.35), 1.0)
	draw_polyline(PackedVector2Array([jc + Vector2(-7, 3), jc + Vector2(0, -4), jc + Vector2(7, 3)]), Color(white, 0.8), 2.0)
