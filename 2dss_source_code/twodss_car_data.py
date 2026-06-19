# =====================================================================
# CAR_DATA.PY  —  Danh sách xe 2D Sideway Showdown
# =====================================================================
# "id"          : key định danh duy nhất
# "name"        : tên hiển thị trên UI
# "brand"       : hãng xe
# "file"        : tên file KHÔNG có đuôi, trong assets/car_model_display/
# "brand_logo"  : tên file trong assets/brandlogo/ (có đuôi), hoặc None
# "free"        : True = miễn phí
# =====================================================================

CAR_LIST = [
    {
        "id"         : "mazda_axela_2012",
        "name"       : "Mazda Axela Sedan 2012",
        "brand"      : "Mazda",
        "file"       : "mazda_axela_2012-displaymode",
        "brand_logo" : "mazda.png",
        "free"       : True,
        "stats"      : {},
    },
    {
        "id"         : "mazda3_fastback_2020",
        "name"       : "Mazda 3 Fastback 2020",
        "brand"      : "Mazda",
        "file"       : "mazda3_fastback_2020-displaymode",
        "brand_logo" : "mazda.png",
        "free"       : True,
        "stats"      : {},
    },
    {
        "id"         : "toyota_ae86_1987",
        "name"       : "Toyota Sprinter AE86 1987",
        "brand"      : "Toyota",
        "file"       : "toyota_ae86_trueno-displaymode",
        "brand_logo" : "toyota.png",
        "free"       : True,
        "stats"      : {},
    },
    {
        "id"         : "toyota_altezza_gita_2003",
        "name"       : "Toyota Altezza Gita 2003",
        "brand"      : "Toyota",
        "file"       : "toyota_altezza_gita-displaymode",
        "brand_logo" : "toyota.png",
        "free"       : True,
        "stats"      : {},
    },
    {
        "id"         : "nissan_gtr_r34",
        "name"       : "Nissan Skyline GT-R34 1999",
        "brand"      : "Nissan",
        "file"       : "nissan_skyline_gtr_r34-displaymode",
        "brand_logo" : "nissan.png",
        "free"       : True,
        "stats"      : {},
    },
    {
        "id"         : "lamborghini_murcielago_sv",
        "name"       : "Lamborghini Murcielago LP670-4 SV 2010",
        "brand"      : "Lamborghini",
        "file"       : "lamborghini_murcielago-displaymode",
        "brand_logo" : "Lamborghini.png",
        "free"       : True,
        "stats"      : {},
    },
    {
        "id"         : "ferrari_f430_2005",
        "name"       : "Ferrari F430 2006",
        "brand"      : "Ferrari",
        "file"       : "ferrari_f430_2005-displaymode",
        "brand_logo" : "Ferrari.png",
        "free"       : True,
        "stats"      : {},
    },
    {
        "id"         : "mclaren_600lt",
        "name"       : "McLaren 600LT",
        "brand"      : "McLaren",
        "file"       : "mclaren_600lt-displaymode",
        "brand_logo" : "mclaren.png",
        "free"       : True,
        "stats"      : {},
    },
    {
        "id"         : "koenigsegg_gemera",
        "name"       : "Koenigsegg Gemera",
        "brand"      : "Koenigsegg",
        "file"       : "koenigsegg_gemera-displaymode",
        "brand_logo" : "Koenigsegg.png",
        "free"       : True,
        "stats"      : {},
    },
    {
        "id"         : "lamborghini_centenario",
        "name"       : "Lamborghini Centenario 2017",
        "brand"      : "Lamborghini",
        "file"       : "lamborghini_centenario-displaymode",
        "brand_logo" : "Lamborghini.png",
        "free"       : True,
        "stats"      : {},
    },
    {
        "id"         : "lamborghini_countach_2021",
        "name"       : "Lamborghini Countach LPI 800-4 2021",
        "brand"      : "Lamborghini",
        "file"       : "lamborghini_countach-lpi800-4-displaymode",
        "brand_logo" : "Lamborghini.png",
        "free"       : True,
        "stats"      : {},
    },
    {
        "id"         : "pagani_utopia",
        "name"       : "Pagani Utopia",
        "brand"      : "Pagani",
        "file"       : "pagani_utopia-displaymode",
        "brand_logo" : "Pagani.png",
        "free"       : True,
        "stats"      : {},
    },
    # ── Scania (Tier S — trucks) ──────────────────────────────────────
    {
        "id"         : "scania_r730_2010",
        "name"       : "Scania R730 Topline 2010",
        "brand"      : "Scania",
        "file"       : "scania-r730-topline-displaymode",
        "brand_logo" : "scania.png",
        "free"       : True,
        "stats"      : {},
    },
    {
        "id"         : "scania_svempa_frostfire",
        "name"       : "Scania Svempa FrostFire",
        "brand"      : "Scania",
        "file"       : "scania-svempa-frostfire-displaymode",
        "brand_logo" : "scania.png",
        "free"       : True,
        "stats"      : {},
    },
]

# =====================================================================
# HELPERS
# =====================================================================
def get_free_cars():
    return [c for c in CAR_LIST if c["free"]]

def get_car_by_id(car_id):
    return next((c for c in CAR_LIST if c["id"] == car_id), None)


# =====================================================================
# CAR_STATS — thông số vật lý dùng trong game engine / track files
# =====================================================================
# Import:  from twodss_car_data import CAR_STATS
#
# ── Physics ──────────────────────────────────────────────────────────
# "max_speed"          : tốc độ tối đa Level 1 (KPH)
# "acceleration"       : gia tốc (units/s²)
# "brake"              : lực phanh
# "friction"           : ma sát tự nhiên
# "tier"               : A → B → C → D → S (S = Scania truck)
#
# ── Upgrade system (future) ──────────────────────────────────────────
# "speed_levels"       : [L1_kph, L2_kph, L3_kph]  — từ xlsx
#
# ── Nitro (nguồn: topdownracing.xlsx) ────────────────────────────────
# "nitro_duration"     : giây kéo dài của 1 lần xài nitro  (10–16)
# "nitro_boost"        : +KPH tối đa khi full boost         (50–77)
# "nitro_boost_time"   : giây để đạt max boost (turbo-lag)  (2.8–4.2)
# "nitro_refill_1per3" : giây để nạp 1/3 thanh nitro        (4.5–6.8)
#
# Công thức dùng trong racer: refill_rate = 33.33 / nitro_refill_1per3
# =====================================================================

CAR_STATS = {
    # ── Tier A — hatchback / sedan ────────────────────────────────────
    "mazda_axela_2012": dict(
        max_speed=188, acceleration=20, brake=17.0, friction=3.5, tier="A",
        speed_levels=[188, 250, 313],
        nitro_duration=10, nitro_boost=50, nitro_boost_time=4.2, nitro_refill_1per3=6.8,
    ),
    "mazda3_fastback_2020": dict(
        max_speed=188, acceleration=20, brake=20.0, friction=3.5, tier="A",
        speed_levels=[188, 250, 313],
        nitro_duration=10, nitro_boost=50, nitro_boost_time=4.0, nitro_refill_1per3=6.8,
    ),
    "toyota_ae86_1987": dict(
        max_speed=188, acceleration=20, brake=23.0, friction=3.5, tier="A",
        speed_levels=[188, 250, 313],
        nitro_duration=10, nitro_boost=50, nitro_boost_time=4.0, nitro_refill_1per3=6.8,
    ),
    "toyota_altezza_gita_2003": dict(
        max_speed=188, acceleration=24, brake=27.6, friction=3.5, tier="A",
        speed_levels=[188, 250, 325],
        nitro_duration=12, nitro_boost=55, nitro_boost_time=3.5, nitro_refill_1per3=5.4,
    ),
    # ── Tier B — sports cars ─────────────────────────────────────────
    "nissan_gtr_r34": dict(
        max_speed=219, acceleration=30, brake=34.5, friction=4.9, tier="B",
        speed_levels=[219, 263, 338],
        nitro_duration=12, nitro_boost=55, nitro_boost_time=3.5, nitro_refill_1per3=5.4,
    ),
    "lamborghini_murcielago_sv": dict(
        max_speed=219, acceleration=32, brake=41.6, friction=4.9, tier="B",
        speed_levels=[219, 263, 369],
        nitro_duration=14, nitro_boost=60, nitro_boost_time=3.2, nitro_refill_1per3=5.0,
    ),
    "ferrari_f430_2005": dict(
        max_speed=219, acceleration=32, brake=44.8, friction=5.6, tier="B",
        speed_levels=[219, 275, 375],
        nitro_duration=14, nitro_boost=60, nitro_boost_time=3.2, nitro_refill_1per3=5.0,
    ),
    # ── Tier C — hypercars ───────────────────────────────────────────
    "mclaren_600lt": dict(
        max_speed=250, acceleration=35, brake=49.0, friction=6.0, tier="C",
        speed_levels=[250, 300, 375],
        nitro_duration=14, nitro_boost=60, nitro_boost_time=3.2, nitro_refill_1per3=5.0,
    ),
    "koenigsegg_gemera": dict(
        max_speed=250, acceleration=45, brake=63.0, friction=5.95, tier="C",
        speed_levels=[250, 300, 375],
        nitro_duration=15, nitro_boost=60, nitro_boost_time=3.2, nitro_refill_1per3=5.0,
    ),
    # ── Tier D — extreme hypercars ───────────────────────────────────
    "lamborghini_centenario": dict(
        max_speed=281, acceleration=50, brake=75.0, friction=5.95, tier="D",
        speed_levels=[281, 330, 400],
        nitro_duration=15, nitro_boost=60, nitro_boost_time=3.2, nitro_refill_1per3=4.5,
    ),
    "lamborghini_countach_2021": dict(
        max_speed=281, acceleration=50, brake=90.0, friction=5.95, tier="D",
        speed_levels=[281, 330, 400],
        nitro_duration=15, nitro_boost=64, nitro_boost_time=3.2, nitro_refill_1per3=4.5,
    ),
    "pagani_utopia": dict(
        max_speed=313, acceleration=60, brake=108.0, friction=7.0, tier="D",
        speed_levels=[313, 460, 500],
        nitro_duration=15, nitro_boost=70, nitro_boost_time=3.2, nitro_refill_1per3=4.5,
    ),
    # ── Tier S — Scania trucks ───────────────────────────────────────
    # Đính chính: Svempa bản 770S là FrostFire (không phải FrostBite)
    "scania_r730_2010": dict(
        max_speed=325, acceleration=52, brake=94.64, friction=6.5, tier="S",
        speed_levels=[325, 460, 540],
        nitro_duration=14, nitro_boost=62, nitro_boost_time=3.0, nitro_refill_1per3=4.5,
    ),
    "scania_svempa_frostfire": dict(
        max_speed=350, acceleration=62, brake=112.84, friction=7.0, tier="S",
        speed_levels=[350, 470, 565],
        nitro_duration=16, nitro_boost=77, nitro_boost_time=2.8, nitro_refill_1per3=4.5,
    ),
}