# ET:Legacy `et.WP_*` constants

Machine-readable copy: [`wp_constants.json`](wp_constants.json).

These values are what you get in JSON as `meansOfDeath` on `obituaries` and `damageStats`. `et.WP_NUM_WEAPONS` is **56** (one past the last real weapon id **55**).

| ID | Lua constant | Description |
|----|--------------|-------------|
| 0 | `et.WP_NONE` | No weapon |
| 1 | `et.WP_KNIFE` | Axis Dagger Knife |
| 2 | `et.WP_LUGER` | Luger |
| 3 | `et.WP_MP40` | MP40 |
| 4 | `et.WP_GRENADE_LAUNCHER` | Axis Hand Grenade |
| 5 | `et.WP_PANZERFAUST` | Panzerfaust |
| 6 | `et.WP_FLAMETHROWER` | Flamethrower |
| 7 | `et.WP_COLT` | Colt 1911 |
| 8 | `et.WP_THOMPSON` | Thompson |
| 9 | `et.WP_GRENADE_PINEAPPLE` | Allies Hand Grenade |
| 10 | `et.WP_STEN` | Sten |
| 11 | `et.WP_MEDIC_SYRINGE` | Syringe |
| 12 | `et.WP_AMMO` | Ammo pack |
| 13 | `et.WP_ARTY` | Artillery |
| 14 | `et.WP_SILENCER` | Silenced Luger |
| 15 | `et.WP_DYNAMITE` | Dynamite |
| 16 | `et.WP_SMOKETRAIL` | Artillery Initial smoke |
| 17 | `et.WP_MAPMORTAR` | Fixed Mortars |
| 18 | `et.VERYBIGEXPLOSION` | Airstrike Explosion effect |
| 19 | `et.WP_MEDKIT` | Medic pack |
| 20 | `et.WP_BINOCULARS` | Binoculars |
| 21 | `et.WP_PLIERS` | Pliers |
| 22 | `et.WP_SMOKE_MARKER` | Airstrike Marker |
| 23 | `et.WP_KAR98` | Kar98 (Axis Rifle) |
| 24 | `et.WP_CARBINE` | M1 Garand (Allies Rifle) |
| 25 | `et.WP_GARAND` | Scoped M1 Garand (Allies Sniper Rifle) |
| 26 | `et.WP_LANDMINE` | Landmine |
| 27 | `et.WP_SATCHEL` | Satchel |
| 28 | `et.WP_SATCHEL_DET` | Satchel Detonator |
| 29 | `et.WP_SMOKE_BOMB` | Smoke Grenade |
| 30 | `et.WP_MOBILE_MG42` | Mobile MG42 |
| 31 | `et.WP_K43` | K43 (Axis Sniper Rifle) |
| 32 | `et.WP_FG42` | FG42 |
| 33 | `et.WP_DUMMY_MG42` | Fixed MG42 |
| 34 | `et.WP_MORTAR` | Allies Mortar |
| 35 | `et.WP_AKIMBO_COLT` | Akimbo Colts 1911 |
| 36 | `et.WP_AKIMBO_LUGER` | Akimbo Lugers |
| 37 | `et.WP_GPG40` | Kar98 (Grenade Loaded) |
| 38 | `et.WP_M7` | M1 Garand (Grenade Loaded) |
| 39 | `et.WP_SILENCED_COLT` | Silenced Colt 1911 |
| 40 | `et.WP_GARAND_SCOPE` | Scoped M1 Garand (Scoped Mode) |
| 41 | `et.WP_K43_SCOPE` | K43 (Scoped Mode) |
| 42 | `et.WP_FG42_SCOPE` | FG42 (Scoped Mode) |
| 43 | `et.WP_MORTAR_SET` | Allies Deployed Mortar |
| 44 | `et.WP_MEDIC_ADRENALINE` | Adrenaline |
| 45 | `et.WP_AKIMBO_SILENCEDCOLT` | Akimbo Silenced Colts 1911 |
| 46 | `et.WP_AKIMBO_SILENCEDLUGER` | Akimbo Silenced Lugers |
| 47 | `et.WP_MOBILE_MG42_SET` | Deployed Mobile MG42 |
| 48 | `et.WP_KNIFE_KABAR` | Allies KA-BAR Knife |
| 49 | `et.WP_MOBILE_BROWNING` | Mobile Browning |
| 50 | `et.WP_MOBILE_BROWNING_SET` | Deployed Mobile Browning |
| 51 | `et.WP_MORTAR2` | Axis Mortar |
| 52 | `et.WP_MORTAR2_SET` | Axis Deployed Mortar |
| 53 | `et.WP_BAZOOKA` | Bazooka |
| 54 | `et.WP_MP34` | MP34 |
| 55 | `et.WP_AIRSTRIKE` | Airstrike |
| — | `et.WP_NUM_WEAPONS` | Count sentinel (**56**) |

## Related (not the same as this table)

Per-player `weaponStats` in [`game-stats-web.lua`](game-stats-web.lua) uses a **28-slot** bitmask (`WS_KNIFE`..`WS_MAX-1`) into `sess.aWeaponStats`, not a direct `et.WP_*` index. Map those slots using ET:L `g_match.c` (or equivalent), not this file alone.
