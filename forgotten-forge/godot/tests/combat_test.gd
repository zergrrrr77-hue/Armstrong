extends SceneTree
## 헤드리스 전투 테스트: 실행  godot --headless --path forgotten-forge/godot -s res://tests/combat_test.gd
## 주인공을 첫 슬라임 옆에 두고 공격 입력을 눌러, 슬라임이 죽는지·주인공이 피해를 받는지 확인한다.

var main: Node
var frame := 0
var slime: Node
var player: Node
var results := {}


func _initialize() -> void:
	main = load("res://scenes/main.tscn").instantiate()
	root.add_child(main)


func _process(_delta: float) -> bool:
	frame += 1
	if frame == 5:
		player = main.player
		for c in main.get_children():
			if c.has_method("take_hit"):
				slime = c
				break
		player.global_position = slime.global_position + Vector2(-22, -4)
		player.facing = 1
		results["slime_hp_start"] = slime.hp
	if frame > 10 and frame < 400:
		# 멀어지면 다가가고, 가까우면 공격 (실제 플레이와 같은 흐름)
		var dx: float = slime.global_position.x - player.global_position.x
		if slime.state != 3 and absf(dx) > 26.0:
			Input.action_release("attack")
			Input.action_press("move_right" if dx > 0 else "move_left")
		else:
			Input.action_release("move_right")
			Input.action_release("move_left")
			Input.action_press("attack")
	if frame == 400:
		Input.action_release("attack")
		Input.action_release("move_right")
		Input.action_release("move_left")
		results["slime_state_after_attacks"] = slime.state
		results["slime_hp_after"] = slime.hp
		# 피격 테스트: 슬라임을 다시 살려 주인공과 겹치게 둔다
		results["player_hp_before_touch"] = player.hp
	if frame == 420:
		var s2: Node = null
		for c in main.get_children():
			if c.has_method("take_hit") and c != slime and c.state != 3:
				s2 = c
				break
		player.global_position = s2.global_position
		player.invuln = 0.0
	if frame == 480:
		results["player_hp_after_touch"] = player.hp
		print("RESULTS ", JSON.stringify(results))
		var ok: bool = results["slime_state_after_attacks"] == 3 and results["player_hp_after_touch"] < results["player_hp_before_touch"]
		print("PASS" if ok else "FAIL")
		return true
	return false
