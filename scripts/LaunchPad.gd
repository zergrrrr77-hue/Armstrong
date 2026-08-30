extends Node3D

## Marks where the ship landed on a planet surface. Interacting with it
## (via Player.gd's proximity interact) launches back to the space scene.

func _ready() -> void:
	add_to_group("interactable")

func interact() -> void:
	get_tree().change_scene_to_file("res://scenes/Main.tscn")
