shader_type spatial;
render_mode blend_add, unshaded, cull_back, depth_draw_never, shadows_disabled;

// 항성을 감싸는 코로나 껍질. 가장자리로 갈수록 밝아지는 프레넬을 뒤집어
// 별 주위로 부드럽게 번지는 빛무리를 만듭니다.

#include "res://shaders/lib/noise.gdshaderinc"

uniform vec3 corona_color : source_color = vec3(1.0, 0.62, 0.22);
uniform float falloff = 3.0;
uniform float intensity = 1.2;
uniform float flicker_speed = 0.15;

varying vec3 v_local;

void vertex() {
	v_local = VERTEX;
}

void fragment() {
	vec3 n = normalize(NORMAL);
	vec3 v = normalize(VIEW);

	// 껍질 중앙(별 원반 위)이 가장 밝고 바깥으로 갈수록 사라지게
	float d = clamp(dot(n, v), 0.0, 1.0);
	float glow = pow(d, falloff);

	// 코로나가 미세하게 일렁이도록
	float flick = 0.88 + 0.12 * fbm3(normalize(v_local) * 4.0 + TIME * flicker_speed);

	ALBEDO = corona_color;
	ALPHA = clamp(glow * intensity * flick, 0.0, 1.0);
}
