shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_burley;

// 행성 지표면의 땅. 단색 평면은 아무리 조명을 잘 줘도 종이처럼 보이기 때문에
// 노이즈로 흙/암반의 색 얼룩과 미세한 요철을 만들어 줍니다.

#include "res://shaders/lib/noise.gdshaderinc"

uniform vec3 color_base : source_color = vec3(0.42, 0.30, 0.18);
uniform vec3 color_alt : source_color = vec3(0.30, 0.22, 0.13);
uniform vec3 color_rock : source_color = vec3(0.22, 0.19, 0.17);
uniform float patch_scale = 0.055;
uniform float grit_scale = 0.9;
uniform float bump_strength = 0.55;

varying vec3 v_world;

void vertex() {
	v_world = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec3 p = v_world * patch_scale;

	// 넓은 색 얼룩 — 토양과 암반이 섞인 느낌
	float patch = fbm5(warp3(p, 0.6));
	vec3 col = mix(color_base, color_alt, smoothstep(0.35, 0.68, patch));

	// 드러난 암반
	float rock = smoothstep(0.60, 0.86, fbm3(p * 2.3 + 11.0));
	col = mix(col, color_rock, rock * 0.7);

	// 잔모래 알갱이
	vec3 g = v_world * grit_scale;
	float grit = fbm3(g);
	col *= 0.86 + 0.28 * grit;

	// 미세 요철 — 빛이 스칠 때 땅이 평평하지 않아 보이게 합니다.
	float eps = 0.45;
	float h0 = fbm3(g);
	float hx = fbm3((v_world + vec3(eps, 0.0, 0.0)) * grit_scale);
	float hz = fbm3((v_world + vec3(0.0, 0.0, eps)) * grit_scale);
	vec3 n = normalize(vec3((h0 - hx) * bump_strength, 0.35, (h0 - hz) * bump_strength));

	ALBEDO = col;
	NORMAL = normalize((VIEW_MATRIX * vec4(n, 0.0)).xyz);
	ROUGHNESS = clamp(0.94 - 0.18 * grit, 0.3, 1.0);
	SPECULAR = 0.25;
}
