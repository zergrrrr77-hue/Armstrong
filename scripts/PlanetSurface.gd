extends Node3D

## 모든 행성이 공유하는 지표면 씬.
## GameState.current_planet_id 를 보고 하늘, 빛, 땅, 자원을 그 행성에 맞게 구성합니다.

const GROUND_SIZE := 120.0
const RESOURCE_COUNT := 7

func _ready() -> void:
	var planet_data := GameState.get_planet(GameState.current_planet_id)
	_setup_environment(planet_data)
	_setup_ground(planet_data)
	_setup_terrain_features(planet_data)
	_setup_launch_pad()
	_setup_resources(planet_data)
	_setup_player()

	HUD.show_controls("WASD: 이동   E: 자원 채집 / 이륙")
	HUD.hide_prompt()
	HUD.update_inventory()

func _setup_environment(planet_data: Dictionary) -> void:
	# 하늘: 대기가 옅은 행성일수록 낮에도 별이 비쳐 보입니다.
	var sun_dir := Vector3(0.42, 0.55, 0.48).normalized()
	var wenv := SpaceVisuals.create_environment({
		"atmosphere_amount": planet_data.get("sky_atmosphere", 0.8),
		"atmosphere_color": planet_data.get("sky_color", Color(0.25, 0.45, 0.9)),
		"horizon_color": planet_data.get("sky_horizon", Color(0.75, 0.85, 1.0)),
		"sun_direction": sun_dir,
		"sun_color": planet_data.get("sun_light_color", Color(1.0, 0.96, 0.9)),
		"sun_size": 0.006,
		"sun_glow_strength": 1.0,
		"star_brightness": 1.0,
		"nebula_strength": 0.8,
		"ambient_energy": 0.30,
		"glow_intensity": 0.45,
		"glow_threshold": 1.20,
	})

	# 대기가 있는 행성은 옅은 안개로 원경이 흐려집니다. 깊이감이 크게 살아납니다.
	var env := wenv.environment
	var haze: float = planet_data.get("sky_atmosphere", 0.8)
	if haze > 0.1:
		env.fog_enabled = true
		env.fog_light_color = planet_data.get("sky_horizon", Color(0.75, 0.85, 1.0))
		env.fog_light_energy = 0.45
		env.fog_density = 0.0022 * haze
		env.fog_sky_affect = 0.0
		env.fog_aerial_perspective = 0.2
	add_child(wenv)

	# 태양광
	var sun := DirectionalLight3D.new()
	sun.name = "SunLight"
	sun.light_color = planet_data.get("sun_light_color", Color(1.0, 0.96, 0.9))
	sun.light_energy = planet_data.get("sun_light_energy", 1.3)
	sun.shadow_enabled = true
	add_child(sun)
	# look_at 은 트리에 들어간 뒤에만 쓸 수 있습니다.
	sun.look_at_from_position(Vector3.ZERO, -sun_dir, Vector3.UP)

func _setup_ground(planet_data: Dictionary) -> void:
	var ground := StaticBody3D.new()
	ground.name = "Ground"

	var mesh_instance := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(GROUND_SIZE, GROUND_SIZE)
	plane.subdivide_width = 32
	plane.subdivide_depth = 32
	mesh_instance.mesh = plane

	var base: Color = planet_data.get("ground_color", Color(0.5, 0.4, 0.3))
	var mat := ShaderMaterial.new()
	mat.shader = load("res://shaders/planet_ground.gdshader")
	mat.set_shader_parameter("color_base", base)
	mat.set_shader_parameter("color_alt", base.darkened(0.28))
	mat.set_shader_parameter("color_rock", base.darkened(0.55))
	mesh_instance.material_override = mat
	ground.add_child(mesh_instance)

	var collision := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = Vector3(GROUND_SIZE, 1.0, GROUND_SIZE)
	collision.shape = shape
	collision.position = Vector3(0, -0.5, 0)
	ground.add_child(collision)

	add_child(ground)

func _setup_terrain_features(planet_data: Dictionary) -> void:
	# 낮은 언덕과 바위. 지평선을 채워 허전함을 없앱니다.
	var rng := RandomNumberGenerator.new()
	rng.seed = int(planet_data["id"])

	var base: Color = planet_data.get("ground_color", Color(0.5, 0.4, 0.3))
	var hill_mat := StandardMaterial3D.new()
	hill_mat.albedo_color = base.darkened(0.18)
	hill_mat.roughness = 0.95

	var rock_mat := StandardMaterial3D.new()
	rock_mat.albedo_color = base.darkened(0.4)
	rock_mat.roughness = 0.9

	for i in range(16):
		var hill := MeshInstance3D.new()
		var sphere := SphereMesh.new()
		var s := rng.randf_range(2.5, 7.0)
		sphere.radius = s
		sphere.height = s * rng.randf_range(0.8, 1.4)
		sphere.radial_segments = 16
		sphere.rings = 8
		sphere.material = hill_mat
		hill.mesh = sphere
		var dist := rng.randf_range(20.0, GROUND_SIZE * 0.5 - 6.0)
		var angle := rng.randf_range(0.0, TAU)
		hill.position = Vector3(cos(angle) * dist, -s * rng.randf_range(0.55, 0.8), sin(angle) * dist)
		add_child(hill)

	for i in range(22):
		var rock := MeshInstance3D.new()
		var box := BoxMesh.new()
		var s := rng.randf_range(0.4, 1.6)
		box.size = Vector3(s, s * rng.randf_range(0.5, 1.2), s * rng.randf_range(0.7, 1.3))
		box.material = rock_mat
		rock.mesh = box
		var dist := rng.randf_range(8.0, GROUND_SIZE * 0.45)
		var angle := rng.randf_range(0.0, TAU)
		rock.position = Vector3(cos(angle) * dist, s * 0.2, sin(angle) * dist)
		rock.rotation = Vector3(rng.randf_range(-0.3, 0.3), rng.randf_range(0.0, TAU), rng.randf_range(-0.3, 0.3))
		add_child(rock)

func _setup_launch_pad() -> void:
	var pad = Node3D.new()
	pad.name = "LaunchPad"
	pad.set_script(load("res://scripts/LaunchPad.gd"))

	var mesh_instance := MeshInstance3D.new()
	var cyl := CylinderMesh.new()
	cyl.top_radius = 2.4
	cyl.bottom_radius = 2.6
	cyl.height = 0.3
	mesh_instance.mesh = cyl
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.55, 0.58, 0.62)
	mat.metallic = 0.7
	mat.roughness = 0.4
	mat.emission_enabled = true
	mat.emission = Color(0.25, 0.45, 0.8)
	mat.emission_energy_multiplier = 0.18
	cyl.material = mat
	pad.add_child(mesh_instance)

	# 착륙한 우주선 — 착륙 다리 대신 수직으로 세워 둡니다.
	var ship := StarshipBuilder.create()
	# -90도로 돌리면 기수가 땅을 향합니다. +90도라야 하늘을 향해 섭니다.
	ship.rotation_degrees = Vector3(90.0, 0.0, 0.0)
	ship.scale = Vector3.ONE * 1.7
	ship.position = Vector3(0.0, StarshipBuilder.TOTAL_LENGTH * 0.5 * 1.7 + 0.1, 0.0)
	pad.add_child(ship)

	pad.position = Vector3(0, 0.15, 0)
	add_child(pad)

func _setup_resources(planet_data: Dictionary) -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = int(planet_data["id"]) + 100

	var res_color: Color = planet_data.get("resource_color", Color(0.8, 0.8, 0.9))

	for i in range(RESOURCE_COUNT):
		var res_node = Node3D.new()
		res_node.name = "Resource_%d" % i
		res_node.set_script(load("res://scripts/ResourceNode.gd"))
		res_node.resource_type = planet_data["resource_name"]

		# 결정 덩어리 — 면이 적은 구는 보석처럼 각져 보입니다.
		var mat := StandardMaterial3D.new()
		mat.albedo_color = res_color
		mat.metallic = 0.3
		mat.roughness = 0.15
		mat.emission_enabled = true
		mat.emission = res_color
		mat.emission_energy_multiplier = 0.22

		for j in range(3):
			var shard := MeshInstance3D.new()
			var gem := SphereMesh.new()
			var s := rng.randf_range(0.22, 0.42)
			gem.radius = s
			gem.height = s * rng.randf_range(2.4, 3.6)
			gem.radial_segments = 6
			gem.rings = 2
			gem.material = mat
			shard.mesh = gem
			shard.position = Vector3(rng.randf_range(-0.3, 0.3), 0.0, rng.randf_range(-0.3, 0.3))
			shard.rotation = Vector3(
				rng.randf_range(-0.35, 0.35),
				rng.randf_range(0.0, TAU),
				rng.randf_range(-0.35, 0.35))
			res_node.add_child(shard)

		# 주변 땅을 물들이는 은은한 빛
		var glow := OmniLight3D.new()
		glow.light_color = res_color
		glow.light_energy = 0.5
		glow.omni_range = 3.2
		glow.position = Vector3(0, 0.6, 0)
		res_node.add_child(glow)

		var dist := rng.randf_range(7.0, GROUND_SIZE * 0.38)
		var angle := rng.randf_range(0.0, TAU)
		res_node.position = Vector3(cos(angle) * dist, 0.35, sin(angle) * dist)

		add_child(res_node)

func _setup_player() -> void:
	var player = CharacterBody3D.new()
	player.name = "Player"
	player.set_script(load("res://scripts/Player.gd"))

	# 우주복 입은 탐사대원
	var suit := StandardMaterial3D.new()
	suit.albedo_color = Color(0.90, 0.91, 0.94)
	suit.roughness = 0.55

	var body_mesh := MeshInstance3D.new()
	var capsule := CapsuleMesh.new()
	capsule.radius = 0.4
	capsule.height = 1.8
	capsule.material = suit
	body_mesh.mesh = capsule
	body_mesh.position = Vector3(0, 0.9, 0)
	player.add_child(body_mesh)

	var visor := MeshInstance3D.new()
	var head := SphereMesh.new()
	head.radius = 0.26
	head.height = 0.52
	visor.mesh = head
	var visor_mat := StandardMaterial3D.new()
	visor_mat.albedo_color = Color(0.12, 0.18, 0.28)
	visor_mat.metallic = 0.9
	visor_mat.roughness = 0.12
	head.material = visor_mat
	visor.position = Vector3(0, 1.62, 0)
	player.add_child(visor)

	var collision := CollisionShape3D.new()
	var shape := CapsuleShape3D.new()
	shape.radius = 0.4
	shape.height = 1.8
	collision.shape = shape
	collision.position = Vector3(0, 0.9, 0)
	player.add_child(collision)

	var camera := Camera3D.new()
	camera.position = Vector3(0, 5.2, 7.0)
	camera.rotation_degrees = Vector3(-32.0, 0.0, 0.0)
	camera.fov = 65.0
	camera.far = 3000.0
	camera.current = true
	player.add_child(camera)

	player.position = Vector3(4.5, 1.0, 6.5)
	add_child(player)
