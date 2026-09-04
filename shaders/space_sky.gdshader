shader_type sky;

// 절차적 별하늘.
// 별 하나하나를 오브젝트로 만들지 않고 방향(EYEDIR)만으로 계산하기 때문에
// 사실상 무한한 개수의 별을 공짜에 가까운 비용으로 그립니다.
// 은하수 띠, 성운, 성간 먼지, 태양 글로우까지 포함합니다.

#include "res://shaders/lib/noise.gdshaderinc"

group_uniforms stars;
uniform float star_brightness = 1.0;
uniform float star_density = 1.0;

group_uniforms nebula;
uniform vec3 nebula_color_a : source_color = vec3(0.26, 0.11, 0.42);
uniform vec3 nebula_color_b : source_color = vec3(0.06, 0.20, 0.45);
uniform vec3 nebula_color_c : source_color = vec3(0.55, 0.18, 0.25);
uniform float nebula_strength = 1.0;
uniform vec3 galactic_axis = vec3(0.35, 0.88, 0.32);

group_uniforms deep_space;
uniform vec3 space_color : source_color = vec3(0.004, 0.005, 0.012);

// 행성 표면에서 쓰는 대기 설정. atmosphere_amount 가 0 이면 순수한 우주입니다.
group_uniforms atmosphere;
uniform float atmosphere_amount = 0.0;
uniform vec3 atmosphere_color : source_color = vec3(0.35, 0.55, 0.95);
uniform vec3 horizon_color : source_color = vec3(0.75, 0.85, 1.0);
uniform vec3 sun_direction = vec3(0.4, 0.6, 0.5);
uniform vec3 sun_color : source_color = vec3(1.0, 0.95, 0.85);
uniform float sun_size = 0.004;
uniform float sun_glow_strength = 1.0;

// 별 한 겹. 방향 공간을 격자로 나누고 각 칸에 별을 하나씩 놓습니다.
vec3 star_layer(vec3 dir, float scale, float cutoff, float size, float bright) {
	vec3 p = dir * scale;
	vec3 id = floor(p);
	vec3 gv = fract(p) - 0.5;

	float h = hash13(id);
	if (h < cutoff) {
		return vec3(0.0);
	}

	// 칸 안에서의 위치를 흩어 격자 느낌을 지웁니다.
	// 칸 경계를 넘어가면 별이 사각형으로 잘리므로, 흩는 폭과 후광 반경의 합이
	// 항상 0.5(칸 반지름)보다 작아야 합니다.
	vec3 off = (hash33(id + 13.7) - 0.5) * 0.40;
	float d = length(gv - off);

	// 밝기 분포: 대부분 어둡고 소수만 밝게 (실제 밤하늘과 같은 분포)
	float t = (h - cutoff) / max(1.0 - cutoff, 0.0001);
	float mag = pow(t, 3.5);

	float core = smoothstep(size, 0.0, d);
	float halo = smoothstep(size * 2.6, 0.0, d) * 0.16;
	float intensity = (core + halo) * bright * (0.12 + 0.88 * mag);

	// 별 색온도: 푸른 백색 ~ 노란 백색 ~ 붉은 거성
	float ct = hash13(id + 3.17);
	vec3 col = mix(vec3(0.70, 0.80, 1.00), vec3(1.00, 0.96, 0.88), smoothstep(0.0, 0.55, ct));
	col = mix(col, vec3(1.00, 0.78, 0.58), smoothstep(0.80, 1.0, ct));

	return col * intensity;
}

void sky() {
	vec3 dir = normalize(EYEDIR);

	// ---- 은하수 띠 ----
	// 은하면에 가까울수록 1에 가까워집니다.
	float band = 1.0 - abs(dot(dir, normalize(galactic_axis)));
	float milky = pow(clamp(band, 0.0, 1.0), 7.0);

	// ---- 성운 ----
	vec3 nd = warp3(dir * 2.6, 0.55);
	float n1 = fbm5(nd);
	float n2 = fbm5(dir * 6.1 + 21.7);
	float clouds = pow(clamp(n1 * 1.35, 0.0, 1.0), 2.4);

	vec3 neb = mix(nebula_color_a, nebula_color_b, clamp(n2 * 1.4, 0.0, 1.0));
	neb = mix(neb, nebula_color_c, pow(clamp(fbm3(dir * 4.2 - 8.3) * 1.3, 0.0, 1.0), 3.0) * 0.6);
	neb *= clouds * milky * nebula_strength * 0.9;

	// 성간 먼지 — 은하수를 가로지르는 어두운 띠
	float dust = pow(clamp(fbm5(dir * 3.4 + 44.1) * 1.5, 0.0, 1.0), 2.0);
	neb *= mix(1.0, 0.15, dust * milky);

	// ---- 별 ----
	// 은하면 쪽에 별이 훨씬 촘촘하게 모이도록 밀도를 조절합니다.
	float dens = star_density * (0.55 + 1.5 * milky);

	// 별은 화면에서 한두 픽셀이어야 진짜 별처럼 보입니다.
	// 크게 그리면 블룸을 먹고 흰 덩어리가 됩니다.
	vec3 stars = vec3(0.0);
	stars += star_layer(dir, 130.0, 1.0 - 0.55 * dens, 0.030, 0.55); // 촘촘한 미광성
	stars += star_layer(dir, 74.0, 1.0 - 0.30 * dens, 0.038, 0.95);  // 중간 밝기
	stars += star_layer(dir, 38.0, 1.0 - 0.11 * dens, 0.048, 1.70);  // 밝은 별

	// 반사 큐브맵 생성 패스에서는 가장 촘촘한 층만 빼서 비용을 아낍니다.
	if (!AT_CUBEMAP_PASS) {
		stars += star_layer(dir, 210.0, 1.0 - 0.62 * dens, 0.026, 0.32);
		// 아주 드문 1등성 — 살짝만 번지게 둡니다.
		stars += star_layer(dir, 17.0, 0.986, 0.052, 2.6);
	}
	stars *= star_brightness;

	// 은하수 중심부의 뿌연 별무리 (개별 별로 분해되지 않는 배경광)
	vec3 haze = mix(vec3(0.30, 0.32, 0.45), vec3(0.55, 0.48, 0.42), n2)
		* milky * pow(clamp(n1 * 1.2, 0.0, 1.0), 1.6) * 0.16;
	haze *= mix(1.0, 0.2, dust * milky);

	vec3 col = space_color + neb + haze + stars;

	// ---- 태양 ----
	vec3 sd = normalize(sun_direction);
	float sun_dot = dot(dir, sd);
	float disc = smoothstep(1.0 - sun_size, 1.0 - sun_size * 0.35, sun_dot);
	float glow = pow(clamp(sun_dot, 0.0, 1.0), 220.0) * 0.9
		+ pow(clamp(sun_dot, 0.0, 1.0), 18.0) * 0.10;
	col += sun_color * (disc * 14.0 + glow * sun_glow_strength);

	// ---- 행성 대기 (지상에서만) ----
	if (atmosphere_amount > 0.001) {
		float up = clamp(dir.y, 0.0, 1.0);
		// 천정은 짙고 지평선은 밝게 — 레일리 산란의 느낌
		vec3 sky_grad = mix(horizon_color, atmosphere_color, pow(up, 0.55));

		// 태양 주변 전방 산란
		float fwd = pow(clamp(sun_dot, 0.0, 1.0), 8.0);
		sky_grad += sun_color * fwd * 0.35;

		// 지평선 아래로는 급격히 어두워집니다.
		float ground_fade = smoothstep(-0.25, 0.02, dir.y);
		sky_grad *= ground_fade;

		// 대기가 짙을수록 별이 씻겨 나갑니다.
		col = mix(col, sky_grad, atmosphere_amount * ground_fade);
	}

	COLOR = col;
}
