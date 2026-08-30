extends CharacterBody3D

## Free-flying spaceship: W/S thrust forward/back, A/D turn left/right.
## No gravity in space, so motion mode is floating and velocity decays
## back to zero when there is no thrust input.

const THRUST_ACCEL = 14.0
const MAX_SPEED = 22.0
const TURN_SPEED = 1.8
const DAMPING = 2.0

func _ready() -> void:
	motion_mode = CharacterBody3D.MOTION_MODE_FLOATING

func _physics_process(delta: float) -> void:
	var turn_input = 0.0
	if Input.is_physical_key_pressed(KEY_A):
		turn_input += 1.0
	if Input.is_physical_key_pressed(KEY_D):
		turn_input -= 1.0
	rotate_y(turn_input * TURN_SPEED * delta)

	var thrust_input = 0.0
	if Input.is_physical_key_pressed(KEY_W):
		thrust_input += 1.0
	if Input.is_physical_key_pressed(KEY_S):
		thrust_input -= 1.0

	var forward = -global_transform.basis.z
	if thrust_input != 0.0:
		velocity = velocity.move_toward(forward * thrust_input * MAX_SPEED, THRUST_ACCEL * delta)
	else:
		velocity = velocity.move_toward(Vector3.ZERO, DAMPING * delta)

	move_and_slide()
