shader_type spatial;
render_mode blend_add, unshaded, cull_disabled, depth_draw_never, shadows_disabled;

// 엔진 화염. 단색 원뿔은 딱딱한 삼각형으로 보이기 때문에,
// 옆모습 실루엣(시선과 표면이 스치는 곳)을 투명하게 만들어
// 기체 상태의 부드러운 불꽃처럼 보이게 합니다.

uniform vec3 nozzle_color : source_color = vec3(0.75, 0.88, 1.0);
uniform vec3 tip_color : source_color = vec3(0.12, 0.30, 0.85);
uniform float plume_length = 0.92;
uniform float intensity = 1.0;
uniform float flicker_speed = 22.0;

varying vec3 v_local;

void vertex() {
	v_local = VERTEX;
}

void fragment() {
	// 노즐(0) → 화염 끝(1)
	float t = clamp(v_local.z / max(plume_length, 0.0001), 0.0, 1.0);

	// 실루엣 가장자리를 부드럽게 — 이것이 원뿔의 각진 느낌을 없앱니다.
	float edge = pow(clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0), 1.5);

	// 끝으로 갈수록 옅어짐
	float fade = pow(1.0 - t, 1.7);

	// 연소 불안정으로 인한 미세한 떨림
	float flick = 0.85 + 0.15 * sin(TIME * flicker_speed + t * 9.0);

	ALBEDO = mix(nozzle_color, tip_color, pow(t, 0.7));
	ALPHA = clamp(fade * edge * intensity * flick, 0.0, 1.0);
}
