// 공용 노이즈 라이브러리.
// 행성 표면, 성운, 구름, 태양 표면 등 모든 절차적 텍스처가 여기 함수를 씁니다.
// 텍스처 파일 없이 셰이더 코드만으로 무한한 디테일을 만들기 위한 것입니다.

float hash13(vec3 p) {
	p = fract(p * 0.1031);
	p += dot(p, p.yzx + 33.33);
	return fract((p.x + p.y) * p.z);
}

vec3 hash33(vec3 p) {
	p = fract(p * vec3(0.1031, 0.1030, 0.0973));
	p += dot(p, p.yxz + 33.33);
	return fract((p.xxy + p.yxx) * p.zyx);
}

// 3D 값 노이즈 (부드러운 보간)
float vnoise(vec3 x) {
	vec3 i = floor(x);
	vec3 f = fract(x);
	f = f * f * (3.0 - 2.0 * f);

	float n000 = hash13(i + vec3(0.0, 0.0, 0.0));
	float n100 = hash13(i + vec3(1.0, 0.0, 0.0));
	float n010 = hash13(i + vec3(0.0, 1.0, 0.0));
	float n110 = hash13(i + vec3(1.0, 1.0, 0.0));
	float n001 = hash13(i + vec3(0.0, 0.0, 1.0));
	float n101 = hash13(i + vec3(1.0, 0.0, 1.0));
	float n011 = hash13(i + vec3(0.0, 1.0, 1.0));
	float n111 = hash13(i + vec3(1.0, 1.0, 1.0));

	return mix(
		mix(mix(n000, n100, f.x), mix(n010, n110, f.x), f.y),
		mix(mix(n001, n101, f.x), mix(n011, n111, f.x), f.y),
		f.z);
}

// 프랙탈 브라운 운동 — 여러 주파수를 겹쳐 자연스러운 형태를 만듭니다.
float fbm3(vec3 p) {
	float s = 0.0;
	float a = 0.5;
	for (int i = 0; i < 3; i++) {
		s += a * vnoise(p);
		p *= 2.02;
		a *= 0.5;
	}
	return s;
}

float fbm5(vec3 p) {
	float s = 0.0;
	float a = 0.5;
	for (int i = 0; i < 5; i++) {
		s += a * vnoise(p);
		p *= 2.02;
		a *= 0.5;
	}
	return s;
}

float fbm7(vec3 p) {
	float s = 0.0;
	float a = 0.5;
	for (int i = 0; i < 7; i++) {
		s += a * vnoise(p);
		p *= 2.02;
		a *= 0.5;
	}
	return s;
}

// 능선 노이즈 — 산맥, 협곡, 용암 균열 같은 날카로운 선형 지형에 씁니다.
float ridged(vec3 p) {
	float s = 0.0;
	float a = 0.5;
	for (int i = 0; i < 5; i++) {
		float n = 1.0 - abs(vnoise(p) * 2.0 - 1.0);
		s += a * n * n;
		p *= 2.03;
		a *= 0.5;
	}
	return s;
}

// 도메인 워핑 — 좌표 자체를 노이즈로 밀어서 대륙처럼 유기적인 형태를 만듭니다.
vec3 warp3(vec3 p, float amount) {
	return p + amount * vec3(
		fbm3(p + vec3(11.3, 5.7, 2.1)),
		fbm3(p + vec3(3.9, 17.2, 8.4)),
		fbm3(p + vec3(23.5, 1.8, 13.6)));
}
