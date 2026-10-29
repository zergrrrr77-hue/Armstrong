extends CharacterBody2D
## 이름 없는 모험가: 이동 · 점프 · 검 공격(길게 누르면 연속) · 피격 · 사망 후 부활.

signal hp_changed(hp: int, max_hp: int)

const SPEED := 95.0
const ACCEL := 900.0
const JUMP_VELOCITY := -370.0
const JUMP_CUT := -150.0
const MAX_FALL := 600.0
const MAX_HP := 50
const ATTACK_DAMAGE := 5
const ATTACK_FRAMES := [2, 3]   # 검이 실제로 맞는 프레임
const HITBOX_X := 15.0

enum State { NORMAL, ATTACK, HURT, DEAD }

var state := State.NORMAL
var hp := MAX_HP
var facing := 1
var invuln := 0.0
var spawn_point := Vector2.ZERO
var fall_limit := 1000.0
var _hit_targets: Array[Node] = []
var _shake := 0.0

@onready var sprite: AnimatedSprite2D = $Sprite
@onready var hitbox: Area2D = $Hitbox
@onready var hitbox_shape: CollisionShape2D = $Hitbox/Shape
@onready var camera: Camera2D = $Camera


func _ready() -> void:
	spawn_point = global_position
	sprite.animation_finished.connect(_on_animation_finished)
	Game.shake_requested.connect(func(a: float) -> void: _shake = maxf(_shake, a))
	sprite.play("idle")


func _physics_process(delta: float) -> void:
	invuln = maxf(0.0, invuln - delta)
	if not is_on_floor():
		velocity.y = minf(velocity.y + get_gravity().y * delta, MAX_FALL)
	var dir := Input.get_axis("move_left", "move_right")

	match state:
		State.NORMAL:
			velocity.x = move_toward(velocity.x, dir * SPEED, ACCEL * delta)
			if dir != 0.0:
				facing = 1 if dir > 0.0 else -1
			if Input.is_action_just_pressed("jump") and is_on_floor():
				velocity.y = JUMP_VELOCITY
			if Input.is_action_just_released("jump") and velocity.y < JUMP_CUT:
				velocity.y = JUMP_CUT
			if Input.is_action_pressed("attack"):
				_start_attack()
		State.ATTACK:
			velocity.x = move_toward(velocity.x, 0.0, ACCEL * 0.4 * delta)
			if sprite.frame in ATTACK_FRAMES:
				_apply_sword_hits()
		State.HURT:
			velocity.x = move_toward(velocity.x, 0.0, 300.0 * delta)
		State.DEAD:
			velocity.x = move_toward(velocity.x, 0.0, 400.0 * delta)

	move_and_slide()
	sprite.flip_h = facing < 0
	hitbox_shape.position.x = HITBOX_X * facing
	if state == State.NORMAL:
		_update_move_animation()
	# 무적 시간에는 깜빡임
	sprite.visible = state == State.DEAD or invuln <= 0.0 or int(invuln * 20.0) % 2 == 0
	if global_position.y > fall_limit and state != State.DEAD:
		take_damage(hp, global_position.x)


func _process(delta: float) -> void:
	if _shake > 0.0:
		_shake = maxf(0.0, _shake - delta * 20.0)
		camera.offset = Vector2(randf_range(-_shake, _shake), randf_range(-_shake, _shake)).round()
	else:
		camera.offset = Vector2.ZERO


func _update_move_animation() -> void:
	if not is_on_floor():
		# 점프 전용 시트가 없어 걷기 프레임 하나로 공중 자세를 낸다
		if sprite.animation != "walk" or sprite.is_playing():
			sprite.play("walk")
			sprite.pause()
		sprite.frame = 0 if velocity.y < 0.0 else 3
	elif absf(velocity.x) > 10.0:
		if sprite.animation != "walk" or not sprite.is_playing():
			sprite.play("walk")
	else:
		if sprite.animation != "idle":
			sprite.play("idle")


func _start_attack() -> void:
	state = State.ATTACK
	_hit_targets.clear()
	velocity.x = facing * 40.0
	sprite.play("attack")


func _apply_sword_hits() -> void:
	for body in hitbox.get_overlapping_bodies():
		if body in _hit_targets or not body.has_method("take_hit"):
			continue
		_hit_targets.append(body)
		body.take_hit(ATTACK_DAMAGE, global_position.x)


func take_damage(amount: int, from_x: float) -> void:
	if invuln > 0.0 or state == State.DEAD:
		return
	hp = maxi(0, hp - amount)
	hp_changed.emit(hp, MAX_HP)
	Game.spawn_text(global_position + Vector2(0, -34), "-%d" % amount, Color(1, 0.35, 0.3))
	Game.shake(4.0)
	if hp <= 0:
		_die()
		return
	state = State.HURT
	invuln = 1.0
	velocity = Vector2((1.0 if global_position.x > from_x else -1.0) * 140.0, -160.0)
	sprite.play("hurt")
	Game.hitstop(0.05)


func _die() -> void:
	state = State.DEAD
	sprite.play("death")
	await get_tree().create_timer(2.2).timeout
	global_position = spawn_point
	velocity = Vector2.ZERO
	hp = MAX_HP
	hp_changed.emit(hp, MAX_HP)
	state = State.NORMAL
	invuln = 1.5
	sprite.play("idle")


func _on_animation_finished() -> void:
	if state == State.ATTACK or state == State.HURT:
		state = State.NORMAL
