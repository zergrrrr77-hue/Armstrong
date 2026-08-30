extends Node3D

## Marks where the ship landed on a planet surface. Interacting with it
## (via Player.gd's proximity interact) launches back to the space scene.

func _ready() -> void:
	add_to_group("interactable")

func get_prompt_text() -> String:
	return "E 키를 눌러 이륙"

func interact() -> void:
	get_tree().change_scene_to_file("res://scenes/Main.tscn")
