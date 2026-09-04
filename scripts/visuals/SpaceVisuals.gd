class_name SpaceVisuals
extends RefCounted

## 우주 비주얼을 조립하는 곳. 하늘(별), 항성, 행성을 만듭니다.
## 게임 로직과 분리되어 있어 다른 프로젝트에도 이 폴더째 옮겨 쓸 수 있습니다.

const SKY_SHADER := "res://shaders/space_sky.gdshader"
const PLANET_SHADER := "res://shaders/planet_surface.gdshader"
const ATMO_SHADER := "res://shaders/planet_atmosphere.gdshader"
const CLOUD_SHADER := "res://shaders/planet_clouds.gdshader"
const STAR_SHADER := "res://shaders/star_surface.gdshader"
const CORONA_SHADER := "res://shaders/star_corona.gdshader"


## 별하늘 + 블룸이 설정된 환경을 만듭니다.
## opts 로 대기(행성 지표면용)를 켤 수 있습니다.
static func create_environment(opts: Dictionary = {}) -> WorldEnvironment:
	var sky_mat := ShaderMaterial.new()
	sky_mat.shader = load(SKY_SHADER)
	sky_mat.set_shader_parameter("star_brightness", opts.get("star_brightness", 1.0))
	sky_mat.set_shader_parameter("star_density", opts.get("star_density", 1.0))
	sky_mat.set_shader_parameter("nebula_strength", opts.get("nebula_strength", 1.0))
	sky_mat.set_shader_parameter("nebula_color_a", opts.get("nebula_color_a", Color(0.26, 0.11, 0.42)))
	sky_mat.set_shader_parameter("nebula_color_b", opts.get("nebula_color_b", Color(0.06, 0.20, 0.45)))
	sky_mat.set_shader_parameter("nebula_color_c", opts.get("nebula_color_c", Color(0.55, 0.18, 0.25)))
	sky_mat.set_shader_parameter("sun_direction", opts.get("sun_direction", Vector3(0.4, 0.55, 0.5)))
	sky_mat.set_shader_parameter("sun_color", opts.get("sun_color", Color(1.0, 0.95, 0.85)))
	sky_mat.set_shader_parameter("sun_size", opts.get("sun_size", 0.004))
	sky_mat.set_shader_parameter("sun_glow_strength", opts.get("sun_glow_strength", 1.0))
	sky_mat.set_shader_parameter("atmosphere_amount", opts.get("atmosphere_amount", 0.0))
	sky_mat.set_shader_parameter("atmosphere_color", opts.get("atmosphere_color", Color(0.35, 0.55, 0.95)))
	sky_mat.set_shader_parameter("horizon_color", opts.get("horizon_color", Color(0.75, 0.85, 1.0)))

	var sky := Sky.new()
	sky.sky_material = sky_mat
	sky.radiance_size = Sky.RADIANCE_SIZE_128

	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	env.sky = sky

	# 하늘빛을 그대로 환경광/반사로 씁니다. 스테인리스강 선체가 별빛을 반사합니다.
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = opts.get("ambient_energy", 0.45)
	env.reflected_light_source = Environment.REFLECTION_SOURCE_SKY

	# 밝은 곳과 어두운 곳의 대비를 필름처럼 정리합니다.
	env.tonemap_mode = Environment.TONE_MAPPER_ACES
	env.tonemap_white = 8.0

	# 블룸 — 별과 태양, 용암, 엔진 화염이 부드럽게 번지게 하는 핵심 효과입니다.
	env.glow_enabled = true
	env.glow_intensity = opts.get("glow_intensity", 0.85)
	env.glow_strength = 1.0
	env.glow_bloom = 0.12
	env.glow_blend_mode = Environment.GLOW_BLEND_MODE_ADDITIVE
	env.glow_hdr_threshold = opts.get("glow_threshold", 1.10)
	env.glow_hdr_scale = 1.6
	# 여러 크기의 번짐을 겹쳐 자연스러운 빛무리를 만듭니다.
	env.set("glow_levels/1", 0.4)
	env.set("glow_levels/2", 0.6)
	env.set("glow_levels/3", 1.0)
	env.set("glow_levels/4", 1.0)
	env.set("glow_levels/5", 0.7)

	var wenv := WorldEnvironment.new()
	wenv.name = "WorldEnvironment"
	wenv.environment = env
	return wenv


## 항성(태양). 끓는 표면 + 코로나 + 광원.
static func create_star(radius: float = 6.0, opts: Dictionary = {}) -> Node3D:
	var star := Node3D.new()
	star.name = "Star"

	var core_color: Color = opts.get("core_color", Color(1.0, 0.96, 0.80))
	var edge_color: Color = opts.get("edge_color", Color(1.0, 0.58, 0.18))

	# 표면
	var surf := MeshInstance3D.new()
	surf.name = "Photosphere"
	surf.mesh = _sphere(radius, 64, 32)
	var smat := ShaderMaterial.new()
	smat.shader = load(STAR_SHADER)
	smat.set_shader_parameter("core_color", core_color)
	smat.set_shader_parameter("edge_color", edge_color)
	smat.set_shader_parameter("spot_color", opts.get("spot_color", Color(0.75, 0.28, 0.05)))
	smat.set_shader_parameter("energy", opts.get("energy", 6.0))
	surf.material_override = smat
	surf.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	star.add_child(surf)

	# 코로나 — 크기가 다른 껍질을 겹쳐 부드럽게 퍼지는 빛무리를 만듭니다.
	var shells := [
		{"scale": 1.18, "intensity": 0.50, "falloff": 2.6},
		{"scale": 1.55, "intensity": 0.22, "falloff": 2.0},
		{"scale": 2.10, "intensity": 0.09, "falloff": 1.5},
	]
	for i in range(shells.size()):
		var shell: Dictionary = shells[i]
		var mi := MeshInstance3D.new()
		mi.name = "Corona%d" % i
		mi.mesh = _sphere(radius * float(shell["scale"]), 32, 16)
		var cmat := ShaderMaterial.new()
		cmat.shader = load(CORONA_SHADER)
		cmat.set_shader_parameter("corona_color", opts.get("corona_color", Color(1.0, 0.62, 0.22)))
		cmat.set_shader_parameter("intensity", shell["intensity"])
		cmat.set_shader_parameter("falloff", shell["falloff"])
		mi.material_override = cmat
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		star.add_child(mi)

	# 행성을 비추는 실제 광원
	var light := OmniLight3D.new()
	light.name = "StarLight"
	light.light_color = opts.get("light_color", Color(1.0, 0.96, 0.90))
	light.light_energy = opts.get("light_energy", 4.0)
	light.omni_range = opts.get("light_range", 400.0)
	light.omni_attenuation = 0.35
	star.add_child(light)

	return star


## 행성 하나의 겉모습. 표면 + 구름 + 대기 껍질을 조립합니다.
## 충돌체나 착륙 판정은 포함하지 않습니다 (호출한 쪽에서 붙입니다).
static func create_planet_visual(data: Dictionary) -> Node3D:
	var root := Node3D.new()
	root.name = "Visual"

	var radius: float = data.get("radius", 4.0)
	root.rotation.z = deg_to_rad(data.get("tilt_deg", 0.0))

	# ---- 지표면 ----
	var spin := _spinner(data.get("spin_speed", 0.04))
	spin.name = "SurfaceSpin"
	root.add_child(spin)

	var surf := MeshInstance3D.new()
	surf.name = "Surface"
	surf.mesh = _sphere(radius, 96, 48)
	surf.material_override = _planet_material(data)
	spin.add_child(surf)

	# ---- 구름 ----
	if data.get("has_clouds", false):
		# 구름은 지표면보다 조금 빠르게 흘러갑니다.
		var cloud_spin := _spinner(data.get("spin_speed", 0.04) * 1.35)
		cloud_spin.name = "CloudSpin"
		root.add_child(cloud_spin)

		var clouds := MeshInstance3D.new()
		clouds.name = "Clouds"
		clouds.mesh = _sphere(radius * 1.012, 64, 32)
		var cmat := ShaderMaterial.new()
		cmat.shader = load(CLOUD_SHADER)
		cmat.set_shader_parameter("cloud_color", data.get("cloud_color", Color(1, 1, 1)))
		cmat.set_shader_parameter("coverage", data.get("cloud_coverage", 0.52))
		cmat.set_shader_parameter("opacity", data.get("cloud_opacity", 1.0))
		cmat.set_shader_parameter("cloud_scale", data.get("cloud_scale", 3.4))
		cmat.set_shader_parameter("seed", data.get("seed", 0.0))
		clouds.material_override = cmat
		clouds.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		cloud_spin.add_child(clouds)

	# ---- 대기 ----
	if data.get("has_atmosphere", false):
		var atmo := MeshInstance3D.new()
		atmo.name = "Atmosphere"
		atmo.mesh = _sphere(radius * data.get("atmo_scale", 1.075), 48, 24)
		var amat := ShaderMaterial.new()
		amat.shader = load(ATMO_SHADER)
		amat.set_shader_parameter("atmo_color", data.get("atmo_color", Color(0.30, 0.55, 1.0)))
		amat.set_shader_parameter("sunset_color", data.get("sunset_color", Color(1.0, 0.45, 0.20)))
		amat.set_shader_parameter("intensity", data.get("atmo_intensity", 1.0))
		amat.set_shader_parameter("rim_power", data.get("atmo_power", 3.2))
		amat.set_shader_parameter("sunset_amount", data.get("sunset_amount", 0.6))
		atmo.material_override = amat
		atmo.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		root.add_child(atmo)

	return root


static func _planet_material(data: Dictionary) -> ShaderMaterial:
	var mat := ShaderMaterial.new()
	mat.shader = load(PLANET_SHADER)
	mat.set_shader_parameter("planet_type", data.get("type", 0))
	mat.set_shader_parameter("seed", data.get("seed", 0.0))
	mat.set_shader_parameter("color_deep", data.get("c_deep", Color(0.01, 0.06, 0.20)))
	mat.set_shader_parameter("color_shallow", data.get("c_shallow", Color(0.05, 0.30, 0.48)))
	mat.set_shader_parameter("color_low", data.get("c_low", Color(0.16, 0.28, 0.10)))
	mat.set_shader_parameter("color_mid", data.get("c_mid", Color(0.33, 0.30, 0.16)))
	mat.set_shader_parameter("color_high", data.get("c_high", Color(0.42, 0.38, 0.33)))
	mat.set_shader_parameter("color_polar", data.get("c_polar", Color(0.92, 0.95, 0.98)))
	mat.set_shader_parameter("sea_level", data.get("sea_level", 0.50))
	mat.set_shader_parameter("terrain_scale", data.get("terrain_scale", 2.2))
	mat.set_shader_parameter("polar_cap", data.get("polar_cap", 0.78))
	mat.set_shader_parameter("bump_strength", data.get("bump_strength", 0.55))
	mat.set_shader_parameter("night_lights", data.get("night_lights", 0.0))
	mat.set_shader_parameter("night_light_color", data.get("night_light_color", Color(1.0, 0.78, 0.42)))
	mat.set_shader_parameter("lava_amount", data.get("lava_amount", 0.0))
	mat.set_shader_parameter("lava_color", data.get("lava_color", Color(1.0, 0.35, 0.05)))
	return mat


## 태양 위치를 셰이더에 알려 밤낮 경계선과 대기 발광을 계산하게 합니다.
static func apply_sun_position(node: Node, sun_pos: Vector3) -> void:
	if node is MeshInstance3D:
		var mat := (node as MeshInstance3D).material_override
		if mat is ShaderMaterial:
			# 해당 셰이더에 sun_position 이 없으면 조용히 무시됩니다.
			(mat as ShaderMaterial).set_shader_parameter("sun_position", sun_pos)
	for child in node.get_children():
		apply_sun_position(child, sun_pos)


static func _sphere(radius: float, segments: int, rings: int) -> SphereMesh:
	var mesh := SphereMesh.new()
	mesh.radius = radius
	mesh.height = radius * 2.0
	mesh.radial_segments = segments
	mesh.rings = rings
	return mesh


static func _spinner(speed: float) -> Spinner:
	var node := Spinner.new()
	node.speed = speed
	return node
