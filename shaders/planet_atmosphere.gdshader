shader_type spatial;
render_mode blend_add, unshaded, cull_back, depth_draw_never, shadows_disabled;

// 행성보다 살짝 큰 껍질 구에 입혀서 대기의 빛나는 테두리를 만듭니다.
// 우주에서 본 지구가 아름다운 가장 큰 이유가 이 푸른 띠입니다.
// 가장자리(시선과 표면이 스치는 각도)일수록 대기를 통과하는 거리가 길어져 밝아집니다.

uniform vec3 atmo_color : source_color = vec3(0.30, 0.55, 1.00);
uniform vec3 sunset_color : source_color = vec3(1.00, 0.45, 0.20);
uniform float rim_power = 3.2;
uniform float intensity = 1.0;
uniform float sunset_amount = 0.6;
uniform vec3 sun_position = vec3(0.0, 0.0, 0.0);

varying vec3 v_world;

void vertex() {
	v_world = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec3 n = normalize(NORMAL);
	vec3 v = normalize(VIEW);

	// 프레넬 — 원반 중앙은 투명, 가장자리로 갈수록 밝게
	float f = 1.0 - clamp(dot(n, v), 0.0, 1.0);
	float rim = pow(f, rim_power);

	// 낮 쪽만 빛나고 밤 쪽 대기는 어둡습니다.
	vec3 center = MODEL_MATRIX[3].xyz;
	vec3 wn = normalize(v_world - center);
	vec3 ldir = normalize(sun_position - v_world);
	float ndl = dot(wn, ldir);
	float day = smoothstep(-0.30, 0.30, ndl);

	// 밤낮 경계선에서는 붉게 물듭니다 (궤도에서 보는 일출/일몰)
	float terminator = smoothstep(0.22, 0.0, abs(ndl));
	vec3 col = mix(atmo_color, sunset_color, terminator * sunset_amount);

	ALBEDO = col;
	ALPHA = clamp(rim * day * intensity, 0.0, 1.0);
}
