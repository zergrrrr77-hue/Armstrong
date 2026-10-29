extends CharacterBody2D
## 초록 슬라임: 가까이 오면 통통 튀며 다가오고, 닿으면 피해를 준다. 죽으면 잠시 뒤 다시 나타난다.

const MAX_HP := 20
const DAMAGE := 3
const AGGRO_RANGE := 150.0
const LEASH := 140.0        # 처음 자리에서 이만큼 넘게는 쫓아가지 않음
const RESPAWN_TIME := 12.0

enum State { IDLE, HOP, HURT, DEAD }

var state := State.IDLE
var hp := MAX_HP
var facing := -1
var hop_timer := 1.0
var air_time := 0.0
var spawn_point := Vector2.ZERO
var player: Node2D

@onready var sprite: AnimatedSprite2D = $Sprite
@onready var touch: Area2D = $Touch


func _ready() -> void:
	spawn_point = global_position
	hop_timer = randf_range(0.4, 1.6)
	sprite.animation_finished.connect(_on_animation_finished)
	sprite.play("idle")


func _physics_process(delta: float) -> void:
	if not is_on_floor():
		velocity.y = minf(velocity.y + get_gravity().y * delta, 600.0)
		air_time += delta
	match state:
		State.IDLE:
			velocity.x = move_toward(velocity.x, 0.0, 400.0 * delta)
			hop_timer -= delta
			if hop_timer <= 0.0 and is_on_floor():
				_hop()
		State.HOP:
			if is_on_floor() and air_time > 0.1:
				state = State.IDLE
				velocity.x = 0.0
				hop_timer = randf_range(0.5, 0.9) if _player_near() else randf_range(1.2, 2.2)
				sprite.play("idle")
		State.HURT, State.DEAD:
			velocity.x = move_toward(velocity.x, 0.0, 300.0 * delta)
	move_and_slide()
	sprite.flip_h = facing < 0
	if state == State.IDLE or state == State.HOP:
		for body in touch.get_overlapping_bodies():
			if body.has_method("take_damage"):
				body.take_damage(DAMAGE, global_position.x)


func _player_near() -> bool:
	return player != null and absf(player.global_position.x - global_position.x) < AGGRO_RANGE \
		and absf(player.global_position.y - global_position.y) < 80.0


func _hop() -> void:
	var dir := float(facing)
	if _player_near():
		dir = signf(player.global_position.x - global_position.x)
	else:
		dir = -1.0 if randf() < 0.5 else 1.0
	# 너무 멀리 가거나 낭떠러지 쪽이면 처음 자리로 돌아간다
	if absf(global_position.x + dir * 40.0 - spawn_point.x) > LEASH:
		dir = signf(spawn_point.x - global_position.x)
	if dir == 0.0:
		dir = 1.0
	facing = int(dir)
	state = State.HOP
	air_time = 0.0
	velocity = Vector2(dir * 60.0, -210.0)
	sprite.play("move")


func take_hit(amount: int, from_x: float) -> void:
	if state == State.DEAD:
		return
	hp -= amount
	var crit := randf() < 0.1
	if crit:
		hp -= amount
	Game.spawn_text(global_position + Vector2(0, -24), str(amount * (2 if crit else 1)), Color(1, 0.88, 0.3) if crit else Color.WHITE, crit)
	Game.hitstop(0.07 if crit else 0.05)
	Game.shake(3.0 if crit else 2.0)
	velocity = Vector2((1.0 if global_position.x > from_x else -1.0) * 85.0, -110.0)
	if hp <= 0:
		_die()
	else:
		state = State.HURT
		sprite.play("hurt")


func _die() -> void:
	state = State.DEAD
	collision_layer = 0
	touch.set_deferred("monitoring", false)
	sprite.play("death")
	await sprite.animation_finished
	visible = false
	await get_tree().create_timer(RESPAWN_TIME).timeout
	global_position = spawn_point
	velocity = Vector2.ZERO
	hp = MAX_HP
	collision_layer = 4
	touch.monitoring = true
	visible = true
	state = State.IDLE
	sprite.play("idle")


func _on_animation_finished() -> void:
	if state == State.HURT:
		state = State.IDLE
		hop_timer = 0.4
		sprite.play("idle")
