class_name StarshipBuilder
extends RefCounted

## 스페이스X 스타십을 본뜬 우주선 모델을 코드로 만듭니다.
## 스테인리스강 동체 + 검은 내열 타일 + 전방 카나드 2장 + 후방 플랩 2장 +
## 랩터 엔진 3기 + 추력에 반응하는 화염.
## 로컬 좌표에서 -Z 가 기수(진행 방향), -Y 가 배(타일이 붙는 면)입니다.

const HULL_RADIUS := 0.28
const NOSE_TIP_Z := -1.95
const BODY_FRONT_Z := -0.55
const TAIL_Z := 1.45
const TOTAL_LENGTH := 3.4

static func create() -> Node3D:
	var ship := Node3D.new()
	ship.name = "StarshipModel"

	_add_hull(ship)
	_add_fins(ship)
	_add_engines(ship)
	_add_plumes(ship)

	return ship

static func _add_hull(parent: Node3D) -> void:
	var profile := PackedVector2Array()
	var r := HULL_RADIUS

	# 후미 — 살짝 좁아지는 엔진 스커트
	profile.append(Vector2(TAIL_Z, 0.0))
	profile.append(Vector2(TAIL_Z, r * 0.70))
	profile.append(Vector2(TAIL_Z - 0.05, r * 0.93))
	profile.append(Vector2(TAIL_Z - 0.14, r))
	# 곧은 동체
	profile.append(Vector2(BODY_FRONT_Z, r))
	# 오자이브 노즈콘 — 부드럽게 한 점으로 모입니다.
	var nose_len := BODY_FRONT_Z - NOSE_TIP_Z
	var steps := 16
	for i in range(1, steps + 1):
		var t := float(i) / float(steps)
		var z := BODY_FRONT_Z - nose_len * t
		var nr: float = r * pow(cos(t * PI * 0.5), 0.62)
		profile.append(Vector2(z, max(nr, 0.0)))

	var mi := MeshInstance3D.new()
	mi.name = "Hull"
	mi.mesh = MeshLab.lathe(profile, 40)

	var mat := ShaderMaterial.new()
	mat.shader = load("res://shaders/ship_hull.gdshader")
	mat.set_shader_parameter("steel_color", Color(0.82, 0.85, 0.90))
	mat.set_shader_parameter("tile_color", Color(0.045, 0.045, 0.055))
	mat.set_shader_parameter("tile_side", 1.0)
	mat.set_shader_parameter("ring_spacing", 3.4)
	mat.set_shader_parameter("weathering", 0.55)
	mi.material_override = mat

	parent.add_child(mi)

static func _add_fins(parent: Node3D) -> void:
	# 검은 내열 타일로 덮인 조종면
	var fin_mat := StandardMaterial3D.new()
	fin_mat.albedo_color = Color(0.075, 0.075, 0.085)
	fin_mat.metallic = 0.05
	fin_mat.roughness = 0.85

	# 후방 플랩 (큼)
	var aft := PackedVector2Array([
		Vector2(0.0, 0.0),
		Vector2(0.62, 0.0),
		Vector2(0.60, 0.40),
		Vector2(0.22, 0.44),
	])
	# 전방 카나드 (작음)
	var fwd := PackedVector2Array([
		Vector2(0.0, 0.0),
		Vector2(0.36, 0.0),
		Vector2(0.35, 0.24),
		Vector2(0.13, 0.26),
	])

	_add_fin_pair(parent, "AftFlap", aft, 0.055, 0.62, fin_mat)
	_add_fin_pair(parent, "Canard", fwd, 0.045, -0.95, fin_mat)

## 좌우 한 쌍의 날개를 답니다. 왼쪽은 오른쪽을 Z축으로 180도 돌려 만들기 때문에
## 거울 반전이 아니라 회전이며, 면의 안팎이 뒤집히지 않습니다.
static func _add_fin_pair(parent: Node3D, base_name: String, outline: PackedVector2Array,
		thickness: float, z_pos: float, mat: Material) -> void:
	var mesh := MeshLab.prism(outline, thickness)

	# 프리즘 로컬축 → 우주선 축 매핑:
	#   프리즘 X(시위) → 우주선 +Z(후방), 프리즘 Y(날개폭) → 우주선 +X, 프리즘 Z(두께) → 우주선 +Y
	var right_basis := Basis(Vector3(0, 0, 1), Vector3(1, 0, 0), Vector3(0, 1, 0))
	var right_pos := Vector3(HULL_RADIUS * 0.85, 0.0, z_pos)

	var roll := Basis(Vector3(0, 0, 1), PI)

	for side in ["R", "L"]:
		var mi := MeshInstance3D.new()
		mi.name = "%s_%s" % [base_name, side]
		mi.mesh = mesh
		mi.material_override = mat
		if side == "R":
			mi.transform = Transform3D(right_basis, right_pos)
		else:
			mi.transform = Transform3D(roll * right_basis, roll * right_pos)
		parent.add_child(mi)

static func _add_engines(parent: Node3D) -> void:
	# 랩터 엔진 노즐
	var bell := PackedVector2Array([
		Vector2(0.00, 0.0),
		Vector2(0.00, 0.048),
		Vector2(0.05, 0.062),
		Vector2(0.14, 0.092),
		Vector2(0.26, 0.125),
		Vector2(0.26, 0.0),
	])
	var mesh := MeshLab.lathe(bell, 20)

	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.13, 0.12, 0.12)
	mat.metallic = 0.85
	mat.roughness = 0.42

	var cluster := Node3D.new()
	cluster.name = "Engines"
	parent.add_child(cluster)

	for i in range(3):
		var a := TAU * float(i) / 3.0 + PI * 0.5
		var mi := MeshInstance3D.new()
		mi.name = "Raptor%d" % i
		mi.mesh = mesh
		mi.material_override = mat
		mi.position = Vector3(cos(a) * 0.125, sin(a) * 0.125, TAIL_Z - 0.02)
		cluster.add_child(mi)

static func _add_plumes(parent: Node3D) -> void:
	# 엔진 화염. 안쪽의 밝고 짧은 심지와 바깥의 흐리고 긴 불꽃을 겹칩니다.
	# 한 겹만 쓰면 색이 평평해서 플라스틱처럼 보입니다.
	var core_profile := PackedVector2Array([
		Vector2(0.00, 0.070),
		Vector2(0.08, 0.088),
		Vector2(0.24, 0.060),
		Vector2(0.46, 0.0),
	])
	var flare_profile := PackedVector2Array([
		Vector2(0.00, 0.100),
		Vector2(0.14, 0.125),
		Vector2(0.42, 0.085),
		Vector2(0.92, 0.0),
	])

	var core_mat := _plume_material(Color(0.90, 0.96, 1.0), Color(0.45, 0.70, 1.0), 0.46, 1.0)
	var flare_mat := _plume_material(Color(0.35, 0.60, 1.0), Color(0.10, 0.22, 0.75), 0.92, 0.55)

	var plumes := Node3D.new()
	plumes.name = "Plumes"
	plumes.visible = false
	parent.add_child(plumes)

	for i in range(3):
		var a := TAU * float(i) / 3.0 + PI * 0.5
		var nozzle := Node3D.new()
		nozzle.name = "Plume%d" % i
		nozzle.position = Vector3(cos(a) * 0.125, sin(a) * 0.125, TAIL_Z + 0.22)

		var flare := MeshInstance3D.new()
		flare.name = "Flare"
		flare.mesh = MeshLab.lathe(flare_profile, 16)
		flare.material_override = flare_mat
		nozzle.add_child(flare)

		var core := MeshInstance3D.new()
		core.name = "Core"
		core.mesh = MeshLab.lathe(core_profile, 16)
		core.material_override = core_mat
		nozzle.add_child(core)

		plumes.add_child(nozzle)

	var light := OmniLight3D.new()
	light.name = "EngineLight"
	light.light_color = Color(0.55, 0.75, 1.0)
	light.light_energy = 0.0
	light.omni_range = 5.0
	light.position = Vector3(0, 0, TAIL_Z + 0.5)
	parent.add_child(light)

static func _plume_material(nozzle: Color, tip: Color, length_units: float,
		intensity: float) -> ShaderMaterial:
	var mat := ShaderMaterial.new()
	mat.shader = load("res://shaders/engine_plume.gdshader")
	mat.set_shader_parameter("nozzle_color", nozzle)
	mat.set_shader_parameter("tip_color", tip)
	mat.set_shader_parameter("plume_length", length_units)
	mat.set_shader_parameter("intensity", intensity)
	return mat

## 모델의 모든 메시를 지정한 렌더 레이어에 올립니다.
## 우주선만 비추는 보조광(fill light)을 걸기 위해 씁니다.
static func set_render_layers(model: Node, layers: int) -> void:
	if model is VisualInstance3D:
		(model as VisualInstance3D).layers = layers
	for child in model.get_children():
		set_render_layers(child, layers)

## 추력(-1 ~ 1)에 맞춰 화염과 불빛을 갱신합니다.
static func set_thrust(model: Node3D, thrust: float, delta: float) -> void:
	var plumes := model.get_node_or_null("Plumes") as Node3D
	var light := model.get_node_or_null("EngineLight") as OmniLight3D
	if plumes == null or light == null:
		return

	var target: float = clamp(thrust, 0.0, 1.0)
	# 점화/소화가 부드럽게 이어지도록 보간합니다.
	var current: float = plumes.get_meta("level", 0.0)
	var level: float = lerp(current, target, clamp(delta * 9.0, 0.0, 1.0))
	plumes.set_meta("level", level)

	plumes.visible = level > 0.02
	if plumes.visible:
		# 화염 길이가 미세하게 떨리도록
		var flicker := 0.90 + 0.10 * sin(Time.get_ticks_msec() * 0.045)
		var width: float = 0.70 + 0.40 * level
		var length: float = (0.45 + 0.85 * level) * flicker
		# 부모를 스케일하면 자식 화염의 "위치"까지 늘어나 엔진에서 떨어져 나갑니다.
		# 각 화염을 따로 늘려야 노즐에 붙어 있습니다.
		for plume in plumes.get_children():
			(plume as Node3D).scale = Vector3(width, width, length)

	light.light_energy = level * 2.4
