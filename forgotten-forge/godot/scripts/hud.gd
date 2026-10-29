extends Control
## 화면 위 정보: 체력 바, 지역 이름, 조작 안내, 세로 화면 경고.

var hp := 50
var max_hp := 50
var _zone_label: Label
var _help_label: Label
var _rotate_label: Label


func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_zone_label = _make_label(13, Color(1, 0.95, 0.85))
	_zone_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_help_label = _make_label(10, Color(1, 1, 1, 0.7))
	_help_label.text = "A D 이동 · W 점프 · J 공격 (길게 누르면 연속)"
	_help_label.visible = not DisplayServer.is_touchscreen_available()
	_rotate_label = _make_label(13, Color.WHITE)
	_rotate_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_rotate_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_rotate_label.text = "화면을 가로로 돌려 주세요"
	get_viewport().size_changed.connect(_layout)
	_layout()


func _make_label(size: int, color: Color) -> Label:
	var l := Label.new()
	var ls := LabelSettings.new()
	ls.font_size = size
	ls.font_color = color
	ls.outline_size = 3
	ls.outline_color = Color(0.1, 0.07, 0.12)
	l.label_settings = ls
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(l)
	return l


func _layout() -> void:
	var s := get_viewport_rect().size
	_zone_label.position = Vector2(0, 52)
	_zone_label.size = Vector2(s.x, 20)
	_help_label.position = Vector2(8, s.y - 18)
	_rotate_label.position = Vector2.ZERO
	_rotate_label.size = s
	_rotate_label.visible = s.y > s.x
	queue_redraw()


func set_hp(value: int, maximum: int) -> void:
	hp = value
	max_hp = maximum
	queue_redraw()


func show_zone(zone_name: String) -> void:
	_zone_label.text = zone_name
	_zone_label.modulate.a = 0.0
	var tw := create_tween()
	tw.tween_property(_zone_label, "modulate:a", 1.0, 0.4)
	tw.tween_interval(1.6)
	tw.tween_property(_zone_label, "modulate:a", 0.0, 0.6)


func _draw() -> void:
	# 체력 바: 픽셀 테두리 + 빨간 게이지
	var x := 8.0
	var y := 8.0
	var w := 90.0
	draw_rect(Rect2(x - 1, y - 1, w + 2, 9), Color(0.1, 0.07, 0.12))
	draw_rect(Rect2(x, y, w, 7), Color(0.23, 0.14, 0.16))
	var ratio := clampf(float(hp) / float(max_hp), 0.0, 1.0)
	draw_rect(Rect2(x, y, w * ratio, 7), Color(0.88, 0.31, 0.25))
	draw_rect(Rect2(x, y, w * ratio, 2), Color(1, 0.55, 0.45))
	draw_string(get_theme_default_font(), Vector2(x + w + 6, y + 7), "%d/%d" % [hp, max_hp], HORIZONTAL_ALIGNMENT_LEFT, -1, 10, Color.WHITE)
	if _rotate_label and _rotate_label.visible:
		draw_rect(Rect2(Vector2.ZERO, get_viewport_rect().size), Color(0.05, 0.04, 0.07, 0.85))
