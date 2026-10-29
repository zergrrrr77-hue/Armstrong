extends Node2D
## 첫 지역 "잊혀진 마을 외곽"을 코드로 조립한다.
## 지형은 문자 격자에 칠한 뒤 이웃을 보고 알맞은 타일(모서리·옆면·물가 등)을 자동으로 고른다.

const TILE := 32
const W := 100
const H := 10
const GROUND_ROW := 7

const TILESET := preload("res://assets/godot/forest_tileset.tres")
const PLAYER_SCENE := preload("res://scenes/player.tscn")
const SLIME_SCENE := preload("res://scenes/slime.tscn")

# 아틀라스 좌표 (assets/README.md의 표와 같음)
const T := {
	"top_l": Vector2i(0, 0), "top": Vector2i(1, 0), "top_r": Vector2i(2, 0), "top_single": Vector2i(3, 0),
	"inner_a": Vector2i(4, 0), "inner_b": Vector2i(5, 0), "left": Vector2i(6, 0), "right": Vector2i(7, 0),
	"bot_l": Vector2i(0, 1), "bot": Vector2i(1, 1), "bot_r": Vector2i(2, 1), "bot_single": Vector2i(3, 1),
	"col_mid": Vector2i(4, 1), "trans_gd": Vector2i(5, 1), "trans_dg": Vector2i(6, 1), "path": Vector2i(7, 1),
	"plat_l": Vector2i(0, 2), "plat_m": Vector2i(1, 2), "plat_r": Vector2i(2, 2), "plat_s": Vector2i(3, 2),
	"stone_top": Vector2i(4, 2), "stone_l": Vector2i(5, 2), "stone_r": Vector2i(6, 2), "stone_brick": Vector2i(7, 2),
	"cliff_tl": Vector2i(0, 3), "cliff_t": Vector2i(1, 3), "cliff_tr": Vector2i(2, 3), "cliff_in": Vector2i(3, 3),
	"cliff_l": Vector2i(4, 3), "cliff_r": Vector2i(5, 3), "cliff_b": Vector2i(6, 3), "cliff_crack": Vector2i(7, 3),
	"water_a": Vector2i(0, 4), "water_b": Vector2i(1, 4), "water_body": Vector2i(2, 4), "water_deep": Vector2i(3, 4),
	"shore_r": Vector2i(4, 4), "shore_l": Vector2i(5, 4), "inner_roots": Vector2i(6, 4), "inner_rock": Vector2i(7, 4),
	"tuft": Vector2i(0, 5), "tall": Vector2i(1, 5), "flowers_a": Vector2i(2, 5), "flowers_b": Vector2i(3, 5),
	"stones": Vector2i(4, 5), "bush": Vector2i(5, 5), "mushroom": Vector2i(6, 5), "fern": Vector2i(7, 5),
}

const OBJECTS := {
	"oak": "res://assets/objects/tree_oak.png", "pine": "res://assets/objects/tree_pine.png",
	"stump": "res://assets/objects/stump.png", "log": "res://assets/objects/log_fallen.png",
	"rock_l": "res://assets/objects/rock_large.png", "rock_s": "res://assets/objects/rock_small.png",
	"fence": "res://assets/objects/fence_mid.png", "fence_end": "res://assets/objects/fence_end.png",
	"fence_broken": "res://assets/objects/fence_broken.png", "flowers": "res://assets/objects/flowers.png",
}

var grid := {}            # Vector2i -> "G"(풀 지면) "D"(흙) "S"(돌길) "P"(발판) "C"(절벽) "W"(물)
var ground_layer: TileMapLayer
var deco_layer: TileMapLayer
var water_cells: Array[Vector2i] = []
var player: CharacterBody2D
var hud: Control


func _ready() -> void:
	_build_background()
	_paint_level()
	ground_layer = _make_layer("Ground", 0)
	deco_layer = _make_layer("Deco", 1)
	_autotile()
	_place_decorations()
	_place_objects()
	_spawn_player(Vector2i(2, GROUND_ROW - 1))
	for x in [22, 30, 36, 55, 62, 86, 94]:
		_spawn_slime(x)
	_build_ui()
	_start_water_animation()


# ───────── 지형 칠하기 ─────────
func _fill(x0: int, x1: int, top: int, top_char := "G", body := "D") -> void:
	for x in range(x0, x1 + 1):
		grid[Vector2i(x, top)] = top_char
		for y in range(top + 1, H):
			grid[Vector2i(x, y)] = body


func _paint_level() -> void:
	_fill(0, 41, GROUND_ROW)
	for x in range(42, 47):           # 물웅덩이
		for y in range(GROUND_ROW, H):
			grid[Vector2i(x, y)] = "W"
	_fill(47, 71, GROUND_ROW)
	for x in range(52, 61):           # 돌길
		grid[Vector2i(x, GROUND_ROW)] = "S"
	_fill(72, 79, GROUND_ROW - 2, "C", "C")   # 절벽 (두 칸 높음)
	_fill(80, W - 1, GROUND_ROW)
	for p in [[24, 27, 4], [43, 45, 5], [30, 31, 2], [62, 64, 4], [88, 90, 4]]:
		for x in range(p[0], p[1] + 1):
			grid[Vector2i(x, p[2])] = "P"


func _is(c: Vector2i, chars: String) -> bool:
	return grid.has(c) and chars.contains(grid[c])


# ───────── 자동 타일 ─────────
func _autotile() -> void:
	for c: Vector2i in grid:
		var ch: String = grid[c]
		var up := c + Vector2i.UP
		var dn := c + Vector2i.DOWN
		var lf := c + Vector2i.LEFT
		var rt := c + Vector2i.RIGHT
		var name := ""
		match ch:
			"G":
				var wl := _is(lf, "W")
				var wr := _is(rt, "W")
				var l := _is(lf, "GDS")
				var r := _is(rt, "GDS")
				if wr:
					name = "shore_r"
				elif wl:
					name = "shore_l"
				elif _is(lf, "S"):
					name = "trans_dg"
				elif _is(rt, "S"):
					name = "trans_gd"
				elif not l and not r:
					name = "top_single"
				elif not l:
					name = "top_l"
				elif not r:
					name = "top_r"
				else:
					name = "top"
			"S":
				name = "stone_top"
			"D":
				var l := _is(lf, "GDS")
				var r := _is(rt, "GDS")
				if not _is(dn, "GDSC") and dn.y < H:
					name = "bot" if l and r else ("bot_l" if r else ("bot_r" if l else "bot_single"))
				elif not l and not r:
					name = "col_mid"
				elif not l:
					name = "left"
				elif not r:
					name = "right"
				else:
					var n := (c.x * 7 + c.y * 13) % 11
					name = "inner_b" if n == 0 else ("inner_roots" if n == 3 else ("inner_rock" if n == 7 and c.y == H - 1 else "inner_a"))
			"P":
				var l := _is(lf, "P")
				var r := _is(rt, "P")
				name = "plat_m" if l and r else ("plat_l" if r else ("plat_r" if l else "plat_s"))
			"C":
				var l := _is(lf, "C")
				var r := _is(rt, "C")
				if not _is(up, "C"):
					name = "cliff_t" if l and r else ("cliff_tl" if r else "cliff_tr")
				elif c.y == H - 1:
					name = "cliff_b"
				elif not l:
					name = "cliff_l"
				elif not r:
					name = "cliff_r"
				else:
					name = "cliff_crack" if (c.x + c.y) % 5 == 0 else "cliff_in"
			"W":
				if not _is(up, "W"):
					name = "water_a"
					water_cells.append(c)
				elif _is(up + Vector2i.UP, "W"):
					name = "water_deep"
				else:
					name = "water_body"
		ground_layer.set_cell(c, 0, T[name])


func _make_layer(layer_name: String, z: int) -> TileMapLayer:
	var layer := TileMapLayer.new()
	layer.name = layer_name
	layer.tile_set = TILESET
	layer.z_index = z
	if layer_name == "Deco":
		layer.collision_enabled = false
	add_child(layer)
	return layer


func _start_water_animation() -> void:
	var timer := Timer.new()
	timer.wait_time = 0.45
	timer.autostart = true
	add_child(timer)
	var frame := [false]
	timer.timeout.connect(func() -> void:
		frame[0] = not frame[0]
		for c in water_cells:
			ground_layer.set_cell(c, 0, T["water_b"] if frame[0] else T["water_a"]))


# ───────── 장식 · 오브젝트 ─────────
func _place_decorations() -> void:
	var deco := {
		4: "tuft", 9: "flowers_a", 13: "tuft", 17: "flowers_b", 21: "tall", 26: "mushroom", 29: "flowers_a",
		34: "bush", 38: "tuft", 40: "stones", 49: "fern", 51: "tuft", 58: "stones", 65: "tuft", 69: "flowers_b",
		82: "fern", 85: "mushroom", 90: "tall", 93: "flowers_a", 97: "bush",
	}
	for x in deco:
		var top := _surface_row(x)
		if top > 0:
			deco_layer.set_cell(Vector2i(x, top - 1), 0, T[deco[x]])
	deco_layer.set_cell(Vector2i(74, GROUND_ROW - 3), 0, T["fern"])
	deco_layer.set_cell(Vector2i(77, GROUND_ROW - 3), 0, T["flowers_b"])


func _surface_row(x: int) -> int:
	for y in range(H):
		if _is(Vector2i(x, y), "GSC"):
			return y
	return -1


func _place_objects() -> void:
	var list := [
		["fence", 5], ["fence", 6], ["fence_end", 7], ["oak", 11], ["stump", 19], ["oak", 33], ["rock_s", 39],
		["flowers", 50], ["rock_l", 64], ["log", 67], ["pine", 75], ["pine", 84], ["oak", 91], ["fence_broken", 96],
	]
	for item in list:
		var tex: Texture2D = load(OBJECTS[item[0]])
		var x: int = item[1]
		var spr := Sprite2D.new()
		spr.texture = tex
		spr.centered = false
		spr.offset = Vector2(-tex.get_width() / 2.0, -tex.get_height())
		spr.position = Vector2(x * TILE + TILE / 2.0, _surface_row(x) * TILE + 4)
		spr.z_index = -1
		add_child(spr)


# ───────── 배경: 하늘 그라데이션 + 시차 언덕 ─────────
func _build_background() -> void:
	var sky_layer := CanvasLayer.new()
	sky_layer.layer = -10
	add_child(sky_layer)
	var grad := Gradient.new()
	grad.set_color(0, Color("4f8fc0"))
	grad.set_color(1, Color("f2e2b0"))
	grad.add_point(0.55, Color("96cede"))
	var tex := GradientTexture2D.new()
	tex.gradient = grad
	tex.fill_from = Vector2(0, 0)
	tex.fill_to = Vector2(0, 1)
	tex.width = 4
	tex.height = 64
	var rect := TextureRect.new()
	rect.texture = tex
	rect.stretch_mode = TextureRect.STRETCH_SCALE
	rect.set_anchors_preset(Control.PRESET_FULL_RECT)
	sky_layer.add_child(rect)
	_hills(0.15, 120.0, 70.0, Color("7a9cb4"), 3)
	_hills(0.35, 70.0, 40.0, Color("6a9a8a"), 7)
	_hills(0.6, 40.0, 26.0, Color("4f8a5e"), 11)


func _hills(scroll: float, base: float, amp: float, color: Color, seed_: int) -> void:
	var par := Parallax2D.new()
	par.scroll_scale = Vector2(scroll, 1.0)
	par.repeat_size = Vector2(960, 0)
	par.repeat_times = 3
	par.z_index = -20 + int(scroll * 10)
	add_child(par)
	var pts := PackedVector2Array()
	var ground_y := GROUND_ROW * TILE + 40.0
	pts.append(Vector2(0, ground_y + 200))
	for i in range(0, 961, 16):
		var t := float(i) / 960.0 * TAU
		var hgt := base + sin(t * 2.0 + seed_) * amp * 0.5 + sin(t * 5.0 + seed_ * 1.7) * amp * 0.3 + sin(t * 11.0 + seed_) * amp * 0.12
		pts.append(Vector2(i, ground_y - hgt).round())
	pts.append(Vector2(960, ground_y + 200))
	var poly := Polygon2D.new()
	poly.polygon = pts
	poly.color = color
	par.add_child(poly)


# ───────── 캐릭터 · UI ─────────
func _spawn_player(cell: Vector2i) -> void:
	player = PLAYER_SCENE.instantiate()
	player.position = Vector2(cell.x * TILE + TILE / 2.0, (cell.y + 1) * TILE + 3)
	player.fall_limit = H * TILE + 40
	add_child(player)
	var cam: Camera2D = player.get_node("Camera")
	cam.limit_left = 0
	cam.limit_right = W * TILE
	cam.limit_top = -64
	cam.limit_bottom = H * TILE


func _spawn_slime(x: int) -> void:
	var s := SLIME_SCENE.instantiate()
	s.position = Vector2(x * TILE + TILE / 2.0, _surface_row(x) * TILE + 3)
	s.player = player
	add_child(s)


func _build_ui() -> void:
	var ui := CanvasLayer.new()
	ui.layer = 10
	add_child(ui)
	hud = preload("res://scripts/hud.gd").new()
	ui.add_child(hud)
	player.hp_changed.connect(hud.set_hp)
	hud.set_hp(player.hp, player.MAX_HP)
	hud.show_zone("잊혀진 마을 외곽")
	var touch := preload("res://scripts/touch_controls.gd").new()
	ui.add_child(touch)
