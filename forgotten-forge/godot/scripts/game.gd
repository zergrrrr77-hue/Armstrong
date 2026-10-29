extends Node
## 전역 도우미 (오토로드 "Game"): 입력 액션 등록, 히트스톱, 화면 흔들림, 떠오르는 대미지 숫자.

signal shake_requested(amount: float)

const KEYS := {
	"move_left": [KEY_A, KEY_LEFT],
	"move_right": [KEY_D, KEY_RIGHT],
	"jump": [KEY_W, KEY_UP, KEY_SPACE],
	"attack": [KEY_J, KEY_Z],
}

var _text_settings: LabelSettings


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	# 키 매핑을 코드로 등록해 project.godot를 단순하게 유지한다
	for action in KEYS:
		if not InputMap.has_action(action):
			InputMap.add_action(action, 0.2)
		for key in KEYS[action]:
			var ev := InputEventKey.new()
			ev.physical_keycode = key
			InputMap.action_add_event(action, ev)
	_text_settings = LabelSettings.new()
	_text_settings.font_size = 10
	_text_settings.outline_size = 3
	_text_settings.outline_color = Color(0.1, 0.07, 0.12)


## 타격 순간 시간을 거의 멈춰 손맛을 만든다.
func hitstop(seconds: float) -> void:
	Engine.time_scale = 0.05
	await get_tree().create_timer(seconds, true, false, true).timeout
	Engine.time_scale = 1.0


func shake(amount: float) -> void:
	shake_requested.emit(amount)


## 월드 좌표 위에 잠깐 떠올랐다 사라지는 글자.
func spawn_text(world_pos: Vector2, text: String, color: Color, big := false) -> void:
	var scene := get_tree().current_scene
	if scene == null:
		return
	var label := Label.new()
	label.text = text
	label.label_settings = _text_settings.duplicate()
	label.label_settings.font_color = color
	if big:
		label.label_settings.font_size = 13
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.size = Vector2(60, 16)
	label.position = world_pos - Vector2(30, 8)
	label.z_index = 50
	scene.add_child(label)
	var tw := label.create_tween()
	tw.set_parallel(true)
	tw.tween_property(label, "position:y", label.position.y - 18, 0.6).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	tw.tween_property(label, "modulate:a", 0.0, 0.3).set_delay(0.35)
	tw.chain().tween_callback(label.queue_free)
