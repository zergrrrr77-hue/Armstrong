shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_burley, specular_schlick_ggx;

// 스타십 선체. 스테인리스강 동체 + 한쪽 면의 검은 내열 타일.
// 실제 스타십의 특징인 가로 용접 링과 타일 격자를 절차적으로 그립니다.
// 선체 길이 방향은 로컬 Z축(-Z가 기수)입니다.

#include "res://shaders/lib/noise.gdshaderinc"

uniform vec3 steel_color : source_color = vec3(0.82, 0.85, 0.90);
uniform vec3 tile_color : source_color = vec3(0.045, 0.045, 0.055);
uniform float tile_side = 1.0;      // 타일이 덮이는 정도 (0이면 전체 스테인리스강)
uniform float ring_spacing = 3.2;   // 용접 링 간격
uniform float weathering = 0.5;     // 사용감(얼룩)

varying vec3 v_local;

void vertex() {
	v_local = VERTEX;
}

void fragment() {
	vec3 p = v_local;

	// 동체 둘레 방향 각도. -Y 쪽(비행 시 아래를 향하는 면)에 내열 타일이 붙습니다.
	float ang = atan(p.x, -p.y);
	float tile_mask = smoothstep(1.15, 0.35, abs(ang)) * tile_side;

	// 타일 경계를 노이즈로 흐트러뜨려 딱 잘린 느낌을 없앱니다.
	tile_mask = clamp(tile_mask + (fbm3(p * 9.0) - 0.5) * 0.28, 0.0, 1.0);
	tile_mask = smoothstep(0.35, 0.65, tile_mask);

	// ---- 스테인리스강 ----
	// 가로 용접 링: 강판을 이어 붙인 자국
	float ring = abs(fract(p.z * ring_spacing) - 0.5) * 2.0;
	float ring_line = smoothstep(0.10, 0.0, 1.0 - ring);
	// 압연 방향으로 미세하게 흐르는 얼룩
	float smudge = fbm5(vec3(p.x * 6.0, p.y * 6.0, p.z * 1.4));

	vec3 steel = steel_color * (0.82 + 0.30 * smudge);
	steel = mix(steel, steel * 0.72, ring_line);
	float steel_rough = mix(0.20, 0.42, smudge * weathering) + ring_line * 0.18;

	// ---- 내열 타일 ----
	// 육각 대신 정사각 타일 격자 (멀리서는 충분히 그럴듯합니다)
	vec2 tuv = vec2(ang * 3.2, p.z * 7.0);
	vec2 g = abs(fract(tuv) - 0.5);
	float grid = smoothstep(0.46, 0.50, max(g.x, g.y));
	float tile_var = fbm3(vec3(floor(tuv), 0.0) * 1.7);

	vec3 tiles = tile_color * (0.75 + 0.5 * tile_var);
	tiles = mix(tiles, tiles * 0.45, grid);

	ALBEDO = mix(steel, tiles, tile_mask);
	// 완전한 금속(METALLIC=1)은 확산광이 없어서, 반사할 것이 없는 우주에서는
	// 새까맣게 보입니다. 금속성을 조금 낮춰 태양빛을 직접 받게 합니다.
	METALLIC = mix(0.45, 0.04, tile_mask);
	ROUGHNESS = clamp(mix(steel_rough, 0.88, tile_mask), 0.12, 1.0);
	SPECULAR = mix(0.75, 0.25, tile_mask);
}
