shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_burley, specular_schlick_ggx;

// 행성 표면. 텍스처 이미지 없이 노이즈만으로 대륙, 협곡, 빙하, 용암을 만듭니다.
// planet_type 하나로 지구형/화성형/얼음/화산 행성을 전부 처리합니다.
//   0 = 지구형 (바다 + 대륙 + 만년설 + 야간 도시 불빛)
//   1 = 화성형 (붉은 사막 + 대협곡 + 극관)
//   2 = 얼음   (빙원 + 크레바스)
//   3 = 화산   (현무암 + 빛나는 용암 균열)

#include "res://shaders/lib/noise.gdshaderinc"

uniform int planet_type : hint_range(0, 3) = 0;
uniform float seed = 0.0;

group_uniforms terrain;
uniform vec3 color_deep : source_color = vec3(0.01, 0.06, 0.20);
uniform vec3 color_shallow : source_color = vec3(0.05, 0.30, 0.48);
uniform vec3 color_low : source_color = vec3(0.16, 0.28, 0.10);
uniform vec3 color_mid : source_color = vec3(0.33, 0.30, 0.16);
uniform vec3 color_high : source_color = vec3(0.42, 0.38, 0.33);
uniform vec3 color_polar : source_color = vec3(0.92, 0.95, 0.98);
uniform float sea_level = 0.50;
uniform float terrain_scale = 2.2;
uniform float polar_cap = 0.78;
uniform float bump_strength = 0.55;

group_uniforms night;
uniform float night_lights = 0.0;
uniform vec3 night_light_color : source_color = vec3(1.0, 0.78, 0.42);

group_uniforms lava;
uniform float lava_amount = 0.0;
uniform vec3 lava_color : source_color = vec3(1.0, 0.35, 0.05);

group_uniforms lighting;
// 태양은 월드 원점에 있습니다. 밤낮 경계선(터미네이터) 계산에 씁니다.
uniform vec3 sun_position = vec3(0.0, 0.0, 0.0);

varying vec3 v_local;
varying vec3 v_world;

// 지형 고도. 도메인 워핑으로 대륙 윤곽을 유기적으로 만듭니다.
float terrain_height(vec3 p) {
	vec3 q = warp3(p * terrain_scale + seed, 0.62);
	return fbm7(q);
}

// 범프용 저가형 고도 (법선 계산에 3번 더 쓰이므로 옥타브를 줄임)
float relief(vec3 p) {
	vec3 q = warp3(p * terrain_scale + seed, 0.62);
	return fbm5(q) + ridged(q * 3.1) * 0.10;
}

void vertex() {
	v_local = normalize(VERTEX);
	v_world = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec3 p = normalize(v_local);
	float lat = abs(p.y);

	float h = terrain_height(p);

	// ---- 지형 기복에 따른 법선 교란 ----
	// 산맥과 협곡이 빛을 받아 입체적으로 보이게 합니다.
	vec3 n_obj = p;
	vec3 t_obj = normalize(cross(vec3(0.0, 1.0, 0.0), n_obj) + vec3(0.0001, 0.0, 0.0));
	vec3 b_obj = cross(n_obj, t_obj);
	float eps = 0.006;
	float r0 = relief(p);
	float rt = relief(normalize(p + t_obj * eps));
	float rb = relief(normalize(p + b_obj * eps));
	vec3 grad = ((rt - r0) * t_obj + (rb - r0) * b_obj) / eps;

	vec3 albedo = vec3(0.5);
	float rough = 0.9;
	float metal = 0.0;
	vec3 emis = vec3(0.0);
	float bump = bump_strength;

	if (planet_type == 0) {
		// ================= 지구형 =================
		float land = smoothstep(sea_level - 0.012, sea_level + 0.012, h);

		// 바다: 깊이에 따라 심해 남색 → 연안 청록
		float depth = clamp((sea_level - h) / 0.16, 0.0, 1.0);
		vec3 ocean = mix(color_shallow, color_deep, depth);

		// 육지: 고도에 따라 초원 → 사막/암반 → 설선
		float e = clamp((h - sea_level) / 0.22, 0.0, 1.0);
		vec3 ground = mix(color_low, color_mid, smoothstep(0.15, 0.6, e));
		ground = mix(ground, color_high, smoothstep(0.55, 0.95, e));

		// 위도에 따른 식생 변화 — 적도는 건조, 중위도는 녹지, 고위도는 툰드라
		float dry = smoothstep(0.32, 0.02, lat) * 0.55 * fbm3(p * 3.7 + 9.1);
		ground = mix(ground, color_mid * 1.15, dry);
		ground = mix(ground, vec3(0.30, 0.31, 0.27), smoothstep(0.52, 0.72, lat) * 0.6);

		// 높은 산맥의 만년설
		float snow = smoothstep(0.72, 0.95, e) * smoothstep(0.15, 0.4, lat + e * 0.35);
		ground = mix(ground, color_polar, snow);

		albedo = mix(ocean, ground, land);

		// 극관 — 노이즈로 가장자리를 들쭉날쭉하게
		float cap = smoothstep(polar_cap, polar_cap + 0.10, lat + fbm3(p * 6.0) * 0.10 - 0.05);
		albedo = mix(albedo, color_polar, cap);

		// 바다는 매끈해 태양 반사가 생기고, 육지는 거칩니다.
		rough = mix(0.06, 0.92, land);
		rough = mix(rough, 0.55, cap);
		bump *= land;

		// ---- 야간 도시 불빛 ----
		if (night_lights > 0.001) {
			vec3 center = MODEL_MATRIX[3].xyz;
			vec3 wn = normalize(v_world - center);
			vec3 ldir = normalize(sun_position - v_world);
			float ndl = dot(wn, ldir);
			float night = smoothstep(0.10, -0.15, ndl);

			// 드문드문한 점으로 흩어져야 도시처럼 보입니다.
			// 넓게 번지면 용암처럼 보이므로 지수를 크게 줍니다.
			float city = pow(clamp(fbm5(p * 46.0 + 31.0), 0.0, 1.0), 11.0);
			// 해안선과 저지대에 도시가 몰리게
			float coast = smoothstep(0.10, 0.0, abs(h - sea_level));
			city *= (0.15 + 0.85 * coast) * land * (1.0 - cap);
			city *= smoothstep(0.80, 0.30, lat);

			emis += night_light_color * city * night * night_lights * 5.0;
		}
	} else if (planet_type == 1) {
		// ================= 화성형 =================
		float v = fbm5(p * 4.1 + seed);
		albedo = mix(color_low, color_mid, smoothstep(0.35, 0.65, h));
		albedo = mix(albedo, color_high, smoothstep(0.60, 0.85, h));

		// 어두운 현무암 평원 (실제 화성의 알베도 무늬)
		float dark = smoothstep(0.55, 0.78, fbm5(p * 2.3 + 17.0));
		albedo = mix(albedo, color_deep, dark * 0.55);

		// 대협곡 — 적도를 따라 이어지는 거대한 균열
		float cy = p.y - 0.04 + 0.09 * fbm3(p * 2.4 + 3.0);
		float extent = smoothstep(-0.75, -0.25, p.x) * smoothstep(0.85, 0.35, p.x);
		float canyon = smoothstep(0.085, 0.008, abs(cy)) * extent;
		albedo = mix(albedo, color_deep * 0.7, canyon * 0.85);

		// 크레이터 자국
		float craters = 1.0 - ridged(p * 14.0 + 7.0);
		albedo *= 0.88 + 0.24 * craters;

		// 극관 — 북극이 더 큽니다.
		float cap_lat = polar_cap - (p.y > 0.0 ? 0.06 : 0.0);
		float cap = smoothstep(cap_lat, cap_lat + 0.09, lat + fbm3(p * 7.0) * 0.09 - 0.045);
		albedo = mix(albedo, color_polar, cap);

		rough = mix(0.95, 0.7, cap);
		bump *= 1.35;
		bump += canyon * 1.2;
	} else if (planet_type == 2) {
		// ================= 얼음 행성 =================
		float cr = ridged(warp3(p * 6.5 + seed, 0.35));
		float cracks = smoothstep(0.60, 0.90, cr);

		albedo = mix(color_mid, color_shallow, smoothstep(0.42, 0.62, h) * 0.65);
		// 크레바스 안쪽은 짙은 청록
		albedo = mix(albedo, color_deep, cracks * 0.85);
		// 얼음 위 눈밭. 흰색을 셰이더에 박아 두면 데이터로 아무리 색을 낮춰도
		// 다시 하얗게 타 버리므로, 반드시 행성 데이터의 색을 씁니다.
		float snowfield = smoothstep(0.55, 0.80, fbm5(p * 5.0 + 21.0));
		albedo = mix(albedo, color_high, snowfield * 0.45);

		rough = mix(0.18, 0.55, cracks);
		bump *= 0.8;
	} else {
		// ================= 화산 행성 =================
		float basalt = fbm5(p * 4.5 + seed);
		albedo = mix(color_deep, color_low, smoothstep(0.35, 0.7, basalt));

		// 재가 덮인 밝은 지대
		float ash = smoothstep(0.62, 0.85, fbm5(p * 2.6 + 12.0));
		albedo = mix(albedo, color_mid, ash * 0.6);

		// 용암 균열 — 능선 노이즈의 마루를 따라 흐릅니다.
		float v = ridged(warp3(p * 5.2 + seed, 0.45));
		float vein = smoothstep(0.78, 0.97, v);
		// 굵은 주맥과 가는 실균열 두 겹
		float fine = smoothstep(0.86, 0.99, ridged(p * 13.0 + 4.0)) * 0.45;
		float glow = clamp(vein + fine, 0.0, 1.0) * lava_amount;

		// 아주 느린 맥동 — 살아있는 행성처럼 보이게
		float pulse = 0.75 + 0.25 * sin(TIME * 0.5 + fbm3(p * 3.0) * 6.28);

		albedo = mix(albedo, lava_color * 0.5, glow * 0.6);
		emis += lava_color * glow * pulse * 3.2;

		rough = mix(0.95, 0.45, glow);
		bump *= 1.2;
	}

	// 교란된 법선을 뷰 공간으로 변환
	vec3 n_pert = normalize(n_obj - grad * bump * 0.02);
	NORMAL = normalize((VIEW_MATRIX * MODEL_MATRIX * vec4(n_pert, 0.0)).xyz);

	ALBEDO = albedo;
	ROUGHNESS = clamp(rough, 0.02, 1.0);
	METALLIC = metal;
	EMISSION = emis;
}
