extends Node

## Persists across scene changes. Holds which planet the player last
## landed on (or is currently on), plus the static data describing
## the solar system's planets and their resources.

var current_planet_id: int = -1

var planets: Array = [
	{
		"id": 0,
		"name": "Rusthaven",
		"color": Color(0.72, 0.32, 0.18),
		"orbit_radius": 30.0,
		"orbit_angle_deg": 0.0,
		"resource_name": "Iron Ore",
		"resource_color": Color(0.55, 0.4, 0.3),
	},
	{
		"id": 1,
		"name": "Glacia",
		"color": Color(0.68, 0.85, 0.95),
		"orbit_radius": 55.0,
		"orbit_angle_deg": 130.0,
		"resource_name": "Ice Crystal",
		"resource_color": Color(0.75, 0.95, 1.0),
	},
	{
		"id": 2,
		"name": "Pyros",
		"color": Color(0.35, 0.12, 0.08),
		"orbit_radius": 80.0,
		"orbit_angle_deg": 250.0,
		"resource_name": "Rare Mineral",
		"resource_color": Color(0.85, 0.65, 0.15),
	},
]

func get_planet(id: int) -> Dictionary:
	for p in planets:
		if p["id"] == id:
			return p
	return planets[0]
