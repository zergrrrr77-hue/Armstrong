# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Armstrong is a Godot 4.x (4.3, Forward+ renderer) 3D prototype implementing "Phase 1" of a space-exploration/resource-gathering game: fly a spaceship between planets, land, walk around on foot, and collect resources into an inventory. The design brief and phase scope live in `DESIGN.md`; user-facing instructions are in `README.md`. Both are written in Korean, as is all in-game UI text (control hints, inventory, interact prompts) — match that language when touching player-facing strings.

There is no separate build system, package manager, or test suite — this is a plain Godot project opened and run through the Godot editor.

## Running the project

- Requires Godot 4.x (4.2+; the project is authored against 4.3) — https://godotengine.org/download
- Open the folder via the Godot project manager (it will detect `project.godot`) and press F5, or run the project's default scene directly: `scenes/Main.tscn`.
- No CLI build/lint/test commands exist in this repo; verification is done by running the game in the editor and exercising the control scheme below.

### Controls

| Context | Input | Action |
|---|---|---|
| Piloting the ship | W/S | Thrust forward/backward |
| Piloting the ship | A/D | Turn left/right |
| Near a planet | E | Land → switches to the planet surface scene |
| On foot | WASD | Move |
| Near a resource | E | Collect → adds to inventory, removes the resource node |
| Near the landing pad | E | Launch → switches back to the space scene |

## Architecture

### Scenes hold no baked geometry — everything is built in code

`scenes/Main.tscn` (space) and `scenes/PlanetSurface.tscn` (planet surface, shared by every planet) are minimal root nodes with only a script attached. All actual geometry — sun, planets, terrain, hills, spaceship, player, resources, landing pad — is procedurally constructed in each script's `_ready()` (`scripts/Main.gd`, `scripts/PlanetSurface.gd`). There is no scene-file editing workflow here: to change what appears in a scene, edit the generator script, not the `.tscn`.

### Autoloads (singletons) carry cross-scene state

Registered in `project.godot` under `[autoload]`:
- **`GameState`** (`autoload/GameState.gd`) — holds `current_planet_id` and the static `planets` array (id, name, color, orbit radius/angle, resource name/color). This is the single source of truth for planet/resource data; adding or tuning a planet means editing this array only — `PlanetSurface.gd` and `Main.gd` both read from it to build their scenes.
- **`Inventory`** (`autoload/Inventory.gd`) — collected-resource counts keyed by resource name, with an `inventory_changed` signal.
- **`HUD`** (`scenes/UI/HUD.tscn`, autoloaded as a *scene* rather than a script) — persistent `CanvasLayer` overlay showing control hints, live inventory, and contextual interact prompts; survives scene changes so it doesn't need to be re-added per scene.

Because these are autoloads, scripts reference them directly by name (`GameState.get_planet(...)`, `Inventory.add_resource(...)`, `HUD.show_prompt(...)`) with no explicit node lookup.

### Scene transition flow

`scripts/LandingZone.gd` (attached to an `Area3D` on each planet in the space scene) detects the ship entering range and, on E, sets `GameState.current_planet_id` and calls `get_tree().change_scene_to_file("res://scenes/PlanetSurface.tscn")`. The surface scene then reads `GameState.current_planet_id` back out via `GameState.get_planet(id)` to configure its terrain color and resource type. `scripts/LaunchPad.gd` reverses this, switching back to `scenes/Main.tscn`. Planet identity is carried purely through this single `GameState` field — there's no per-planet scene or saved state beyond it.

### Interaction system

Interactable objects (`ResourceNode.gd`, `LaunchPad.gd`) add themselves to the `"interactable"` group in `_ready()` and expose `get_prompt_text()` / `interact()`. `scripts/Player.gd` scans that group every physics frame for the nearest node within `INTERACT_RANGE`, shows/hides the HUD prompt accordingly, and calls `interact()` on an edge-triggered E press. Adding a new interactable type means implementing those two methods and joining the group — no changes to `Player.gd` are needed.

### Movement

- `Spaceship.gd`: `CharacterBody3D` in `MOTION_MODE_FLOATING` (no gravity); W/S apply thrust along the local -Z axis toward `MAX_SPEED`, A/D rotate around Y, and velocity damps back to zero with no input.
- `Player.gd`: `CharacterBody3D` with manual gravity, WASD mapped to world-space X/Z (camera is a fixed child so screen orientation stays constant).

Both read `Input.is_physical_key_pressed(...)` directly rather than via the Input Map / actions — keep new input handling consistent with that pattern unless there's a reason to introduce input actions project-wide.

## Fonts / localization

`project.godot` sets `gui/theme/custom_font` to `assets/fonts/NanumGothic-Regular.ttf` (SIL OFL 1.1) because Godot's built-in font lacks Hangul glyphs, needed since all UI text is Korean.
