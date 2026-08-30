extends CanvasLayer

## Persistent UI overlay (autoloaded as a scene, so it survives scene
## changes between the space scene and planet surfaces). Shows control
## hints, the live inventory, and contextual interact prompts.

@onready var controls_label: Label = $ControlsLabel
@onready var inventory_label: Label = $InventoryLabel
@onready var prompt_label: Label = $PromptLabel

func _ready() -> void:
	Inventory.inventory_changed.connect(_on_inventory_changed)
	_on_inventory_changed()
	prompt_label.visible = false

func show_controls(text: String) -> void:
	controls_label.text = text

func show_prompt(text: String) -> void:
	prompt_label.text = text
	prompt_label.visible = true

func hide_prompt() -> void:
	prompt_label.visible = false

func update_inventory() -> void:
	_on_inventory_changed()

func _on_inventory_changed() -> void:
	var lines: PackedStringArray = ["Inventory:"]
	var resources = Inventory.get_all()
	if resources.is_empty():
		lines.append("(empty)")
	else:
		for key in resources.keys():
			lines.append("%s: %d" % [key, resources[key]])
	inventory_label.text = "\n".join(lines)
