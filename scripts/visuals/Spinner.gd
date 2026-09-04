class_name Spinner
extends Node3D

## 노드를 Y축으로 천천히 돌립니다. 행성 자전과 구름 이동에 씁니다.

var speed: float = 0.05

func _process(delta: float) -> void:
	rotate_y(speed * delta)
