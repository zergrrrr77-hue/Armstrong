extends Area3D

## Attached to each planet's landing trigger volume in the space scene.
## While the spaceship is inside, pressing E lands on this planet.

var planet_id: int = 0
var planet_display_name: String = "Planet"

var _ship_in_range := false
var _e_was_pressed := false

func _ready() -> void:
	body_entered.connect(_on_body_entered)
	body_exited.connect(_on_body_exited)

func _on_body_entered(body: Node) -> void:
	if body.is_in_group("player_ship"):
		_ship_in_range = true
		HUD.show_prompt("Press E to land on %s" % planet_display_name)

func _on_body_exited(body: Node) -> void:
	if body.is_in_group("player_ship"):
		_ship_in_range = false
		HUD.hide_prompt()

func _process(_delta: float) -> void:
	var e_now = Input.is_physical_key_pressed(KEY_E)
	if _ship_in_range and e_now and not _e_was_pressed:
		GameState.current_planet_id = planet_id
		get_tree().change_scene_to_file("res://scenes/PlanetSurface.tscn")
	_e_was_pressed = e_now
