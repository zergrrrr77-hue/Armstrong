class_name MeshLab
extends RefCounted

## 코드로 메시를 만드는 도구 모음.
## 외부 3D 모델 파일 없이 우주선 같은 형태를 직접 생성하기 위한 것입니다.

## 회전체(선반 깎기). profile 의 각 점은 (축방향 위치, 반지름).
## 축은 Z 이며, 우주선은 -Z 가 기수 방향입니다.
static func lathe(profile: PackedVector2Array, segments: int = 32) -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)

	for i in range(profile.size() - 1):
		var a := profile[i]
		var b := profile[i + 1]
		for s in range(segments):
			var t0 := TAU * float(s) / float(segments)
			var t1 := TAU * float(s + 1) / float(segments)
			var c0 := cos(t0)
			var n0 := sin(t0)
			var c1 := cos(t1)
			var n1 := sin(t1)

			var v00 := Vector3(c0 * a.y, n0 * a.y, a.x)
			var v01 := Vector3(c1 * a.y, n1 * a.y, a.x)
			var v10 := Vector3(c0 * b.y, n0 * b.y, b.x)
			var v11 := Vector3(c1 * b.y, n1 * b.y, b.x)

			# 반지름이 0인 끝단에서는 삼각형 하나만 필요합니다.
			if a.y <= 0.0001:
				_tri(st, v00, v11, v10)
			elif b.y <= 0.0001:
				_tri(st, v00, v01, v10)
			else:
				_tri(st, v00, v01, v11)
				_tri(st, v00, v11, v10)

	st.generate_normals()
	# UV 가 없는 절차적 메시라 탄젠트는 만들지 않습니다 (노멀맵을 쓰지 않으므로 불필요).
	return st.commit()

## 볼록 다각형을 Z 방향으로 밀어낸 각기둥. 우주선 날개(핀)에 씁니다.
static func prism(points: PackedVector2Array, thickness: float) -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)

	var hz := thickness * 0.5
	var count := points.size()

	# 앞/뒤 면 (삼각형 부채꼴)
	for i in range(1, count - 1):
		var p0 := points[0]
		var p1 := points[i]
		var p2 := points[i + 1]
		_tri(st,
			Vector3(p0.x, p0.y, hz),
			Vector3(p1.x, p1.y, hz),
			Vector3(p2.x, p2.y, hz))
		_tri(st,
			Vector3(p0.x, p0.y, -hz),
			Vector3(p2.x, p2.y, -hz),
			Vector3(p1.x, p1.y, -hz))

	# 옆면
	for i in range(count):
		var a := points[i]
		var b := points[(i + 1) % count]
		var a0 := Vector3(a.x, a.y, hz)
		var a1 := Vector3(a.x, a.y, -hz)
		var b0 := Vector3(b.x, b.y, hz)
		var b1 := Vector3(b.x, b.y, -hz)
		_tri(st, a0, a1, b1)
		_tri(st, a0, b1, b0)

	st.generate_normals()
	# UV 가 없는 절차적 메시라 탄젠트는 만들지 않습니다 (노멀맵을 쓰지 않으므로 불필요).
	return st.commit()

static func _tri(st: SurfaceTool, a: Vector3, b: Vector3, c: Vector3) -> void:
	st.add_vertex(a)
	st.add_vertex(b)
	st.add_vertex(c)
