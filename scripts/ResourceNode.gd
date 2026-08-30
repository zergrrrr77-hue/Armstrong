extends Node3D

## A collectible resource on a planet surface. Interacting with it
## (via Player.gd's proximity interact) adds it to the Inventory and
## removes the node from the world.

var resource_type: String = "Mineral"
var amount: int = 1

func _ready() -> void:
	add_to_group("interactable")

func get_prompt_text() -> String:
	return "E 키를 눌러 %s 채집" % resource_type

func interact() -> void:
	Inventory.add_resource(resource_type, amount)
	queue_free()
