extends CharacterBody3D

## On-foot controller: WASD moves the player in world-space axes
## (camera is a fixed child, so it always frames the action). E
## interacts with the nearest resource / launch pad within range.

const SPEED = 6.0
const GRAVITY = 20.0
const INTERACT_RANGE = 2.5

var _nearest_interactable = null
var _e_was_pressed := false

func _physics_process(delta: float) -> void:
	if not is_on_floor():
		velocity.y -= GRAVITY * delta
	else:
		velocity.y = 0.0

	var input_dir = Vector3.ZERO
	if Input.is_physical_key_pressed(KEY_W):
		input_dir.z -= 1.0
	if Input.is_physical_key_pressed(KEY_S):
		input_dir.z += 1.0
	if Input.is_physical_key_pressed(KEY_A):
		input_dir.x -= 1.0
	if Input.is_physical_key_pressed(KEY_D):
		input_dir.x += 1.0
	if input_dir.length() > 0.0:
		input_dir = input_dir.normalized()

	velocity.x = input_dir.x * SPEED
	velocity.z = input_dir.z * SPEED

	move_and_slide()

	_update_nearest_interactable()

	var e_now = Input.is_physical_key_pressed(KEY_E)
	if e_now and not _e_was_pressed and _nearest_interactable != null:
		_nearest_interactable.interact()
	_e_was_pressed = e_now

func _update_nearest_interactable() -> void:
	var nearest = null
	var nearest_dist = INTERACT_RANGE
	for node in get_tree().get_nodes_in_group("interactable"):
		var d = global_position.distance_to(node.global_position)
		if d <= nearest_dist:
			nearest_dist = d
			nearest = node
	_nearest_interactable = nearest
	if nearest != null:
		HUD.show_prompt(nearest.get_prompt_text())
	else:
		HUD.hide_prompt()
