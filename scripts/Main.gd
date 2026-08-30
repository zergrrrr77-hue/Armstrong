extends Node3D

## Space scene: builds the sun, planets, and the player's spaceship at
## runtime. Reusing a single script for all "space" content keeps this
## a plain, hand-editable Node3D scene with no baked-in geometry.

const SPACESHIP_DEFAULT_POS = Vector3(0, 0, 15)

func _ready() -> void:
	_setup_environment()
	_setup_sun()
	_setup_planets()
	_setup_spaceship()
	HUD.show_controls("W/S: Thrust   A/D: Turn   E: Land near a planet")
	HUD.hide_prompt()
	HUD.update_inventory()

func _setup_environment() -> void:
	var env = WorldEnvironment.new()
	var environment = Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color(0.02, 0.02, 0.05)
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color(0.15, 0.15, 0.2)
	environment.ambient_light_energy = 1.0
	env.environment = environment
	add_child(env)

func _setup_sun() -> void:
	var sun = MeshInstance3D.new()
	sun.name = "Sun"
	var mesh = SphereMesh.new()
	mesh.radius = 6.0
	mesh.height = 12.0
	sun.mesh = mesh
	var mat = StandardMaterial3D.new()
	mat.albedo_color = Color(1.0, 0.85, 0.4)
	mat.emission_enabled = true
	mat.emission = Color(1.0, 0.8, 0.3)
	mat.emission_energy_multiplier = 2.5
	sun.material_override = mat
	add_child(sun)

	var light = OmniLight3D.new()
	light.light_energy = 3.0
	light.omni_range = 200.0
	sun.add_child(light)

func _setup_planets() -> void:
	for planet_data in GameState.planets:
		_create_planet(planet_data)

func _create_planet(data: Dictionary) -> void:
	var body = StaticBody3D.new()
	body.name = "Planet_%s" % data["name"]

	var mesh_instance = MeshInstance3D.new()
	var sphere = SphereMesh.new()
	sphere.radius = 4.0
	sphere.height = 8.0
	mesh_instance.mesh = sphere
	var mat = StandardMaterial3D.new()
	mat.albedo_color = data["color"]
	mesh_instance.material_override = mat
	body.add_child(mesh_instance)

	var collision = CollisionShape3D.new()
	var shape = SphereShape3D.new()
	shape.radius = 4.0
	collision.shape = shape
	body.add_child(collision)

	var landing_zone = Area3D.new()
	landing_zone.name = "LandingZone"
	landing_zone.set_script(load("res://scripts/LandingZone.gd"))
	landing_zone.planet_id = data["id"]
	landing_zone.planet_display_name = data["name"]
	var lz_collision = CollisionShape3D.new()
	var lz_shape = SphereShape3D.new()
	lz_shape.radius = 9.0
	lz_collision.shape = lz_shape
	landing_zone.add_child(lz_collision)
	body.add_child(landing_zone)

	var angle = deg_to_rad(data["orbit_angle_deg"])
	var radius = data["orbit_radius"]
	body.position = Vector3(cos(angle) * radius, 0, sin(angle) * radius)

	add_child(body)

func _setup_spaceship() -> void:
	var ship = CharacterBody3D.new()
	ship.name = "Spaceship"
	ship.add_to_group("player_ship")
	ship.set_script(load("res://scripts/Spaceship.gd"))

	var mesh_instance = MeshInstance3D.new()
	var box = BoxMesh.new()
	box.size = Vector3(1.2, 0.6, 2.0)
	mesh_instance.mesh = box
	var mat = StandardMaterial3D.new()
	mat.albedo_color = Color(0.7, 0.75, 0.85)
	mesh_instance.material_override = mat
	ship.add_child(mesh_instance)

	var collision = CollisionShape3D.new()
	var shape = BoxShape3D.new()
	shape.size = Vector3(1.2, 0.6, 2.0)
	collision.shape = shape
	ship.add_child(collision)

	var camera = Camera3D.new()
	camera.position = Vector3(0, 4, 9)
	camera.rotation_degrees = Vector3(-20, 0, 0)
	camera.current = true
	ship.add_child(camera)

	var start_pos = SPACESHIP_DEFAULT_POS
	if GameState.current_planet_id != -1:
		var pd = GameState.get_planet(GameState.current_planet_id)
		var angle = deg_to_rad(pd["orbit_angle_deg"])
		var radius = pd["orbit_radius"]
		var planet_pos = Vector3(cos(angle) * radius, 0, sin(angle) * radius)
		start_pos = planet_pos + Vector3(0, 0, 12)
	ship.position = start_pos

	add_child(ship)
