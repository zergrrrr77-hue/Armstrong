extends Node

## Persists across scene changes. Tracks collected resources by name.

signal inventory_changed

var resources: Dictionary = {}

func add_resource(resource_name: String, amount: int = 1) -> void:
	resources[resource_name] = resources.get(resource_name, 0) + amount
	inventory_changed.emit()

func get_count(resource_name: String) -> int:
	return resources.get(resource_name, 0)

func get_all() -> Dictionary:
	return resources
