extends Node3D

## 우주 씬. 별하늘, 태양, 행성들, 우주선을 런타임에 조립합니다.
## 실제 겉모습은 scripts/visuals/ 의 빌더들이 만들고, 여기서는 배치와 게임 로직만 다룹니다.

const SUN_RADIUS := 6.0
const SUN_POSITION := Vector3.ZERO
## 1번(기본) + 2번 레이어. 2번은 우주선 전용 보조광이 쓰는 레이어입니다.
const SHIP_RENDER_LAYERS := 3
const SHIP_FILL_CULL_MASK := 2

func _ready() -> void:
	_setup_environment()
	_setup_star()
	_setup_planets()

	var ship := _setup_spaceship()
	_setup_camera(ship)
	_setup_ship_fill_light()

	# 각 행성 셰이더에 태양 위치를 알려 밤낮 경계와 대기 발광을 계산하게 합니다.
	SpaceVisuals.apply_sun_position(self, SUN_POSITION)

	HUD.show_controls("W/S: 전진/후진   A/D: 방향 전환   E: 행성 근처에서 착륙")
	HUD.hide_prompt()
	HUD.update_inventory()

func _setup_environment() -> void:
	add_child(SpaceVisuals.create_environment({
		"star_brightness": 1.0,
		"star_density": 1.0,
		"nebula_strength": 0.8,
		"ambient_energy": 0.35,
		"glow_intensity": 0.7,
		"glow_threshold": 1.12,
		# 하늘에 그리는 태양 광원 방향은 우주선 기준이 아니라 고정 배경이므로
		# 실제 태양(원점) 대신 은은한 기본값만 씁니다.
		"sun_size": 0.0,
		"sun_glow_strength": 0.0,
	}))

func _setup_star() -> void:
	var star := SpaceVisuals.create_star(SUN_RADIUS, {
		"core_color": Color(1.0, 0.97, 0.82),
		"edge_color": Color(1.0, 0.58, 0.18),
		"corona_color": Color(1.0, 0.66, 0.26),
		"energy": 6.5,
		"light_energy": 7.0,
		"light_range": 900.0,
	})
	star.position = SUN_POSITION
	add_child(star)

func _setup_planets() -> void:
	for planet_data in GameState.planets:
		_create_planet(planet_data)

func _create_planet(data: Dictionary) -> void:
	var radius: float = data["radius"]

	var body := StaticBody3D.new()
	body.name = "Planet_%s" % data["name"]
	body.position = GameState.get_planet_position(data)

	# 겉모습 (지표면 + 구름 + 대기)
	body.add_child(SpaceVisuals.create_planet_visual(data))

	# 우주선이 뚫고 지나가지 않도록
	var collision := CollisionShape3D.new()
	var shape := SphereShape3D.new()
	shape.radius = radius
	collision.shape = shape
	body.add_child(collision)

	# 착륙 판정 범위
	var landing_zone = Area3D.new()
	landing_zone.name = "LandingZone"
	landing_zone.set_script(load("res://scripts/LandingZone.gd"))
	landing_zone.planet_id = data["id"]
	landing_zone.planet_display_name = data["name"]
	var lz_collision := CollisionShape3D.new()
	var lz_shape := SphereShape3D.new()
	lz_shape.radius = radius * 1.7 + 3.0
	lz_collision.shape = lz_shape
	landing_zone.add_child(lz_collision)
	body.add_child(landing_zone)

	add_child(body)

func _setup_spaceship() -> CharacterBody3D:
	var ship = CharacterBody3D.new()
	ship.name = "Spaceship"
	ship.add_to_group("player_ship")
	ship.set_script(load("res://scripts/Spaceship.gd"))

	var model := StarshipBuilder.create()
	# 우주선만 2번 레이어에도 올려 전용 보조광을 받게 합니다.
	StarshipBuilder.set_render_layers(model, SHIP_RENDER_LAYERS)
	ship.add_child(model)

	var collision := CollisionShape3D.new()
	var shape := CapsuleShape3D.new()
	shape.radius = StarshipBuilder.HULL_RADIUS
	shape.height = StarshipBuilder.TOTAL_LENGTH
	collision.shape = shape
	# 캡슐은 기본이 Y축이라 기체 길이 방향(Z)에 맞춰 눕힙니다.
	collision.rotation_degrees = Vector3(90.0, 0.0, 0.0)
	ship.add_child(collision)

	# 출발 위치: 첫 화면에서 행성이 아름답게 보이도록 구도를 잡습니다.
	# 태양을 등지고 서야 행성의 낮 쪽이 보입니다. 정면이 아니라 옆으로 비껴서면
	# 밤낮 경계선이 함께 들어와 훨씬 입체적으로 보입니다.
	var focus: Dictionary = GameState.get_planet(GameState.current_planet_id)
	var planet_pos := GameState.get_planet_position(focus)
	var to_sun := (SUN_POSITION - planet_pos).normalized()
	if to_sun.length_squared() < 0.001:
		to_sun = Vector3.FORWARD
	var side := to_sun.cross(Vector3.UP).normalized()
	var dist: float = focus["radius"] * 3.2 + 7.0
	ship.position = planet_pos \
		+ to_sun * dist * 0.72 \
		+ side * dist * 0.62 \
		+ Vector3.UP * dist * 0.20

	add_child(ship)
	# 기수를 행성 쪽으로 돌립니다 (look_at 은 -Z 를 대상으로 향하게 합니다).
	# 행성 정중앙을 겨누면 우주선이 행성을 정확히 가립니다.
	# 조준점을 살짝 비껴 두면 행성이 화면에서 온전히 보입니다.
	ship.look_at(planet_pos + side * focus["radius"] * 1.15 - Vector3.UP * focus["radius"] * 0.45, Vector3.UP)
	return ship

## 우주선만 비추는 약한 보조광.
## 우주는 광원이 태양 하나뿐이라 그늘진 면이 새까맣게 묻히는데,
## 이 빛은 레이어 마스크 덕분에 행성의 밤낮 표현은 건드리지 않습니다.
func _setup_ship_fill_light() -> void:
	var fill := DirectionalLight3D.new()
	fill.name = "ShipFillLight"
	fill.light_color = Color(0.62, 0.72, 1.0)
	fill.light_energy = 0.6
	fill.shadow_enabled = false
	fill.light_cull_mask = SHIP_FILL_CULL_MASK
	add_child(fill)
	fill.look_at_from_position(Vector3.ZERO, Vector3(-0.5, -0.75, -0.45), Vector3.UP)

func _setup_camera(ship: Node3D) -> void:
	var cam := ChaseCamera.new()
	cam.name = "ChaseCamera"
	cam.target = ship
	cam.offset = Vector3(-0.75, 2.05, 7.0)
	cam.look_ahead = 13.0
	cam.look_up = 1.35
	cam.fov = 70.0
	cam.far = 8000.0
	cam.current = true
	add_child(cam)
