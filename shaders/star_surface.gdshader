shader_type spatial;
render_mode blend_mix, unshaded, cull_back, shadows_disabled;

// 항성(태양) 표면. 대류 세포(granulation), 흑점, 채층의 불꽃을 표현합니다.
// 밝기를 1.0 이상으로 크게 내보내 블룸이 코로나처럼 번지게 합니다.

#include "res://shaders/lib/noise.gdshaderinc"

uniform vec3 core_color : source_color = vec3(1.0, 0.95, 0.75);
uniform vec3 edge_color : source_color = vec3(1.0, 0.55, 0.15);
uniform vec3 spot_color : source_color = vec3(0.75, 0.28, 0.05);
uniform float energy = 6.0;
uniform float flow_speed = 0.03;

varying vec3 v_local;

void vertex() {
	v_local = normalize(VERTEX);
}

void fragment() {
	vec3 p = normalize(v_local);
	float t = TIME * flow_speed;

	// 대류 세포 — 표면이 끓는 듯한 무늬
	vec3 q = warp3(p * 7.0 + vec3(t, t * 0.6, -t * 0.8), 0.45);
	float gran = fbm5(q);
	float fine = fbm5(q * 3.2 + 5.0);

	// 흑점 — 드물게 나타나는 어두운 자기 영역
	float spots = smoothstep(0.60, 0.30, fbm5(p * 2.4 + 40.0));

	vec3 col = mix(edge_color, core_color, smoothstep(0.30, 0.70, gran * 0.7 + fine * 0.3));
	col = mix(col, spot_color, spots * 0.7);

	// 주변부 감광(limb darkening) — 실제 태양처럼 가장자리가 어둡게
	float limb = clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	float darken = 0.45 + 0.55 * pow(limb, 0.55);

	ALBEDO = vec3(0.0);
	EMISSION = col * energy * darken;
}
