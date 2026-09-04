extends Node

## 씬이 바뀌어도 유지됩니다. 지금 착륙한 행성과, 태양계 전체의 정의를 들고 있습니다.
##
## 행성을 추가하거나 바꾸려면 아래 planets 배열만 수정하면 됩니다.
## 겉모습(색, 대기, 구름, 용암)까지 전부 여기 데이터로 결정됩니다.
##
## type: 0 = 지구형, 1 = 화성형, 2 = 얼음, 3 = 화산

var current_planet_id: int = -1

var planets: Array = [
	{
		"id": 0,
		"name": "Terra",
		"resource_name": "생체 시료",
		"resource_color": Color(0.45, 0.90, 0.55),

		# 궤도와 크기
		"orbit_radius": 58.0,
		"orbit_angle_deg": 15.0,
		"radius": 4.6,
		"spin_speed": 0.035,
		"tilt_deg": 23.0,

		# 표면
		"type": 0,
		"seed": 3.7,
		"c_deep": Color(0.008, 0.045, 0.16),
		"c_shallow": Color(0.03, 0.32, 0.50),
		"c_low": Color(0.13, 0.27, 0.09),
		"c_mid": Color(0.38, 0.33, 0.17),
		"c_high": Color(0.45, 0.41, 0.36),
		"c_polar": Color(0.95, 0.97, 1.0),
		"sea_level": 0.505,
		"terrain_scale": 2.1,
		"polar_cap": 0.80,
		"bump_strength": 0.6,
		"night_lights": 1.0,
		"night_light_color": Color(1.0, 0.76, 0.40),

		# 구름과 대기
		"has_clouds": true,
		"cloud_coverage": 0.50,
		"cloud_scale": 3.2,
		"cloud_opacity": 0.95,
		"cloud_color": Color(1.0, 1.0, 1.0),
		"has_atmosphere": true,
		"atmo_color": Color(0.28, 0.55, 1.0),
		"sunset_color": Color(1.0, 0.48, 0.22),
		"atmo_intensity": 0.85,
		"atmo_power": 5.5,
		"atmo_scale": 1.038,
		"sunset_amount": 0.45,

		# 지표면 씬
		"ground_color": Color(0.28, 0.34, 0.18),
		"sky_atmosphere": 0.92,
		"sky_color": Color(0.11, 0.26, 0.60),
		"sky_horizon": Color(0.40, 0.54, 0.78),
		"sun_light_color": Color(1.0, 0.97, 0.92),
		"sun_light_energy": 1.5,
	},
	{
		"id": 1,
		"name": "Rusthaven",
		"resource_name": "철광석",
		"resource_color": Color(0.72, 0.42, 0.28),

		"orbit_radius": 104.0,
		"orbit_angle_deg": 140.0,
		"radius": 3.5,
		"spin_speed": 0.030,
		"tilt_deg": 25.0,

		"type": 1,
		"seed": 11.2,
		"c_deep": Color(0.22, 0.11, 0.07),
		"c_shallow": Color(0.45, 0.22, 0.12),
		"c_low": Color(0.52, 0.26, 0.14),
		"c_mid": Color(0.70, 0.38, 0.21),
		"c_high": Color(0.82, 0.53, 0.34),
		"c_polar": Color(0.94, 0.94, 0.92),
		"sea_level": 0.50,
		"terrain_scale": 2.6,
		"polar_cap": 0.84,
		"bump_strength": 0.75,

		"has_clouds": false,
		"has_atmosphere": true,
		"atmo_color": Color(0.85, 0.52, 0.32),
		"sunset_color": Color(0.95, 0.60, 0.35),
		"atmo_intensity": 0.45,
		"atmo_power": 6.0,
		"atmo_scale": 1.028,
		"sunset_amount": 0.35,

		"ground_color": Color(0.55, 0.27, 0.15),
		"sky_atmosphere": 0.75,
		"sky_color": Color(0.34, 0.21, 0.15),
		"sky_horizon": Color(0.54, 0.36, 0.23),
		"sun_light_color": Color(1.0, 0.88, 0.75),
		"sun_light_energy": 1.1,
	},
	{
		"id": 2,
		"name": "Glacia",
		"resource_name": "얼음 결정",
		"resource_color": Color(0.72, 0.94, 1.0),

		"orbit_radius": 152.0,
		"orbit_angle_deg": 245.0,
		"radius": 4.0,
		"spin_speed": 0.022,
		"tilt_deg": 8.0,

		"type": 2,
		"seed": 27.5,
		"c_deep": Color(0.05, 0.22, 0.40),
		"c_shallow": Color(0.40, 0.62, 0.78),
		"c_low": Color(0.50, 0.62, 0.72),
		"c_mid": Color(0.58, 0.70, 0.79),
		"c_high": Color(0.72, 0.81, 0.87),
		"c_polar": Color(0.84, 0.90, 0.94),
		"sea_level": 0.50,
		"terrain_scale": 2.4,
		"polar_cap": 0.70,
		"bump_strength": 0.5,

		"has_clouds": true,
		"cloud_coverage": 0.70,
		"cloud_scale": 4.2,
		"cloud_opacity": 0.32,
		"cloud_color": Color(0.92, 0.97, 1.0),
		"has_atmosphere": true,
		"atmo_color": Color(0.55, 0.80, 1.0),
		"sunset_color": Color(0.75, 0.70, 0.95),
		"atmo_intensity": 0.70,
		"atmo_power": 5.0,
		"atmo_scale": 1.034,
		"sunset_amount": 0.40,

		"ground_color": Color(0.78, 0.88, 0.95),
		"sky_atmosphere": 0.70,
		"sky_color": Color(0.18, 0.32, 0.56),
		"sky_horizon": Color(0.48, 0.60, 0.76),
		"sun_light_color": Color(0.92, 0.96, 1.0),
		"sun_light_energy": 0.9,
	},
	{
		"id": 3,
		"name": "Pyros",
		"resource_name": "희귀 광물",
		"resource_color": Color(1.0, 0.72, 0.25),

		"orbit_radius": 205.0,
		"orbit_angle_deg": 320.0,
		"radius": 3.2,
		"spin_speed": 0.045,
		"tilt_deg": 12.0,

		"type": 3,
		"seed": 44.8,
		"c_deep": Color(0.045, 0.035, 0.040),
		"c_shallow": Color(0.10, 0.07, 0.07),
		"c_low": Color(0.16, 0.12, 0.11),
		"c_mid": Color(0.30, 0.22, 0.19),
		"c_high": Color(0.40, 0.30, 0.25),
		"c_polar": Color(0.35, 0.28, 0.25),
		"sea_level": 0.50,
		"terrain_scale": 2.8,
		"polar_cap": 1.20,
		"bump_strength": 0.85,
		"lava_amount": 1.0,
		"lava_color": Color(1.0, 0.36, 0.06),

		"has_clouds": true,
		"cloud_coverage": 0.70,
		"cloud_scale": 3.8,
		"cloud_opacity": 0.45,
		"cloud_color": Color(0.30, 0.24, 0.22),
		"has_atmosphere": true,
		"atmo_color": Color(1.0, 0.40, 0.15),
		"sunset_color": Color(1.0, 0.30, 0.10),
		"atmo_intensity": 0.65,
		"atmo_power": 5.0,
		"atmo_scale": 1.032,
		"sunset_amount": 0.40,

		"ground_color": Color(0.16, 0.13, 0.12),
		"sky_atmosphere": 0.55,
		"sky_color": Color(0.13, 0.055, 0.045),
		"sky_horizon": Color(0.38, 0.13, 0.065),
		"sun_light_color": Color(1.0, 0.80, 0.65),
		"sun_light_energy": 0.85,
	},
]

func get_planet(id: int) -> Dictionary:
	for p in planets:
		if p["id"] == id:
			return p
	return planets[0]

## 행성이 태양 주위 어디에 놓이는지 계산합니다. 우주 씬과 우주선 배치가 같은 값을 씁니다.
func get_planet_position(data: Dictionary) -> Vector3:
	var angle: float = deg_to_rad(data["orbit_angle_deg"])
	var radius: float = data["orbit_radius"]
	return Vector3(cos(angle) * radius, 0.0, sin(angle) * radius)
