# 🎮 Enemy Territory Mechanics & Balancer Rules — etl-stats-server

## Stopwatch Game Mechanics

Gathers are played under **Stopwatch** rules — two rounds on the same map, teams swap sides.

- **Axis**: Always the **defender** by default on our maps.
- **Allies**: Always the **attacker** (trying to complete objectives within the time limit).
- **Round 1**: Allies attempt to complete the map objective. If they succeed, a stopwatch time is set. If not, it's a fullhold.
- **Round 2**: Teams swap. Allies must beat the Round 1 time (or complete within the map limit if fullhold).
- **Double Fullhold → Draw**: If Axis defends successfully in both rounds, the match is parsed as a **Draw**.

---

## Character Classes & Core Roles

Only three classes are **Core** for gathers:
1. **Medic**: Team survival, healing, revives.
2. **Field Ops**: Ammo distribution, artillery/airstrikes.
3. **Engineer**: The most objective-critical class. **All maps require an Engineer.**

---

## Engineer Division (Critical for Balancer)

Engineers are split into two distinct types that **must never be mixed** in balancer logic:

1. **Rifle Engineer** (Primary): Grenade-launching rifle (Garand/K43). The critical engineering role — must be balanced across teams.
2. **SMG Engineer** (Secondary): Submachine gun (Thompson/MP40). Handles specific build phases. Must be tracked separately — two SMG engineers ≠ one Rifle Engineer.

---

## SR & Balancer Objective

- All SR tracking and ratings calculations exist to serve the **team balancer**.
- When adjusting ratings or balancer algorithms, preserve core role preferences (Medic and Rifle Engineer) to generate highly competitive, balanced matchups.
- The SR delta between teams should be minimized when generating balanced team assignments.
