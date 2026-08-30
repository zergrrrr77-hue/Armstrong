extends Node3D

## Shared planet-surface scene: builds ground, decorative hills, a
## launch pad, scattered resources, and the player, all configured
## from GameState.current_planet_id.

const GROUND_SIZE = 80.0
const RESOURCE_COUNT = 6

func _ready() -> void:
	var planet_data = GameState.get_planet(GameState.current_planet_id)
	_setup_environment(planet_data)
	_setup_ground(planet_data)
	_setup_decorative_hills(planet_data)
	_setup_launch_pad()
	_setup_resources(planet_data)
	_setup_player()
	HUD.show_controls("WASD: Move   E: Collect resources / Launch")
	HUD.hide_prompt()
	HUD.update_inventory()

func _setup_environment(planet_data: Dictionary) -> void:
	var env = WorldEnvironment.new()
	var environment = Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = planet_data["color"].darkened(0.6)
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = planet_data["color"].lightened(0.3)
	environment.ambient_light_energy = 0.6
	env.environment = environment
	add_child(env)

	var sun_light = DirectionalLight3D.new()
	sun_light.rotation_degrees = Vector3(-50, -30, 0)
	sun_light.light_energy = 1.2
	add_child(sun_light)

func _setup_ground(planet_data: Dictionary) -> void:
	var ground = StaticBody3D.new()
	ground.name = "Ground"

	var mesh_instance = MeshInstance3D.new()
	var plane = PlaneMesh.new()
	plane.size = Vector2(GROUND_SIZE, GROUND_SIZE)
	mesh_instance.mesh = plane
	var mat = StandardMaterial3D.new()
	mat.albedo_color = planet_data["color"]
	mesh_instance.material_override = mat
	ground.add_child(mesh_instance)

	var collision = CollisionShape3D.new()
	var shape = BoxShape3D.new()
	shape.size = Vector3(GROUND_SIZE, 1.0, GROUND_SIZE)
	collision.shape = shape
	collision.position = Vector3(0, -0.5, 0)
	ground.add_child(collision)

	add_child(ground)

func _setup_decorative_hills(planet_data: Dictionary) -> void:
	var rng = RandomNumberGenerator.new()
	rng.seed = planet_data["id"]
	for i in range(10):
		var hill = MeshInstance3D.new()
		var sphere = SphereMesh.new()
		var s = rng.randf_range(1.5, 4.0)
		sphere.radius = s
		sphere.height = s * 1.2
		hill.mesh = sphere
		var mat = StandardMaterial3D.new()
		mat.albedo_color = planet_data["color"].darkened(0.15)
		hill.material_override = mat
		var dist = rng.randf_range(15.0, GROUND_SIZE / 2.0 - 5.0)
		var angle = rng.randf_range(0, TAU)
		hill.position = Vector3(cos(angle) * dist, -s * 0.7, sin(angle) * dist)
		add_child(hill)

func _setup_launch_pad() -> void:
	var pad = Node3D.new()
	pad.name = "LaunchPad"
	pad.set_script(load("res://scripts/LaunchPad.gd"))

	var mesh_instance = MeshInstance3D.new()
	var cyl = CylinderMesh.new()
	cyl.top_radius = 2.0
	cyl.bottom_radius = 2.2
	cyl.height = 0.3
	mesh_instance.mesh = cyl
	var mat = StandardMaterial3D.new()
	mat.albedo_color = Color(0.8, 0.8, 0.9)
	mat.emission_enabled = true
	mat.emission = Color(0.3, 0.6, 1.0)
	mat.emission_energy_multiplier = 0.8
	mesh_instance.material_override = mat
	pad.add_child(mesh_instance)

	pad.position = Vector3(0, 0.15, 0)
	add_child(pad)

func _setup_resources(planet_data: Dictionary) -> void:
	var rng = RandomNumberGenerator.new()
	rng.seed = planet_data["id"] + 100
	for i in range(RESOURCE_COUNT):
		var res_node = Node3D.new()
		res_node.name = "Resource_%d" % i
		res_node.set_script(load("res://scripts/ResourceNode.gd"))
		res_node.resource_type = planet_data["resource_name"]

		var mesh_instance = MeshInstance3D.new()
		var box = BoxMesh.new()
		box.size = Vector3(0.6, 0.6, 0.6)
		mesh_instance.mesh = box
		var mat = StandardMaterial3D.new()
		mat.albedo_color = planet_data["resource_color"]
		mat.emission_enabled = true
		mat.emission = planet_data["resource_color"]
		mat.emission_energy_multiplier = 0.5
		mesh_instance.material_override = mat
		res_node.add_child(mesh_instance)

		var dist = rng.randf_range(6.0, GROUND_SIZE / 2.0 - 8.0)
		var angle = rng.randf_range(0, TAU)
		res_node.position = Vector3(cos(angle) * dist, 0.3, sin(angle) * dist)

		add_child(res_node)

func _setup_player() -> void:
	var player = CharacterBody3D.new()
	player.name = "Player"
	player.set_script(load("res://scripts/Player.gd"))

	var mesh_instance = MeshInstance3D.new()
	var capsule = CapsuleMesh.new()
	capsule.radius = 0.4
	capsule.height = 1.8
	mesh_instance.mesh = capsule
	mesh_instance.position = Vector3(0, 0.9, 0)
	var mat = StandardMaterial3D.new()
	mat.albedo_color = Color(0.9, 0.9, 0.95)
	mesh_instance.material_override = mat
	player.add_child(mesh_instance)

	var collision = CollisionShape3D.new()
	var shape = CapsuleShape3D.new()
	shape.radius = 0.4
	shape.height = 1.8
	collision.shape = shape
	collision.position = Vector3(0, 0.9, 0)
	player.add_child(collision)

	var camera = Camera3D.new()
	camera.position = Vector3(0, 6, 8)
	camera.rotation_degrees = Vector3(-35, 0, 0)
	camera.current = true
	player.add_child(camera)

	player.position = Vector3(4, 1.0, 6)
	add_child(player)
