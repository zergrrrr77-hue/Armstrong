shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_burley;

// 지표면 위에 뜬 얇은 구름 껍질. 별도의 구에 입혀 천천히 회전시키면
// 행성이 살아 움직이는 것처럼 보입니다.

#include "res://shaders/lib/noise.gdshaderinc"

uniform vec3 cloud_color : source_color = vec3(1.0, 1.0, 1.0);
uniform float cloud_scale = 3.4;
uniform float coverage = 0.52;
uniform float softness = 0.16;
uniform float seed = 0.0;
uniform float opacity = 1.0;

varying vec3 v_local;

void vertex() {
	v_local = normalize(VERTEX);
}

void fragment() {
	vec3 p = normalize(v_local);

	// 위도 방향으로 눌러서 편서풍처럼 띠 모양으로 늘어지게 만듭니다.
	vec3 q = vec3(p.x, p.y * 2.1, p.z) * cloud_scale + seed;
	q = warp3(q, 0.5);

	float n = fbm7(q);
	// 소용돌이(저기압) 느낌을 주는 두 번째 층
	float swirl = fbm5(q * 2.7 + 13.0);
	n = n * 0.75 + swirl * 0.25;

	float a = smoothstep(coverage, coverage + softness, n);

	// 적도 수렴대 / 아열대 고압대 — 구름이 위도별로 몰리고 비는 패턴
	float lat = abs(p.y);
	float belt = 0.55 + 0.45 * cos(lat * 9.0);
	a *= clamp(belt, 0.0, 1.0);

	ALBEDO = cloud_color;
	ALPHA = clamp(a * opacity, 0.0, 1.0);
	ROUGHNESS = 1.0;
	SPECULAR = 0.15;
}
