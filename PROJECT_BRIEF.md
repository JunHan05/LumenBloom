# PROJECT BRIEF — "Lumen Bloom"

> **How to use this file:** This is the single source of truth for the game. If you are Claude Code (or any developer) reading this, treat every name, mechanic, filename, and folder path here as canonical. Do not rename characters, enemies, abilities, or files unless explicitly told to. When in doubt, match this document exactly.

---

## 1. WHAT WE ARE BUILDING

**Lumen Bloom** is a **2D side-scrolling action platformer** built in **Python using Pygame**. It is a university group coursework artefact for the module **CT029-3-2 Imaging and Special Effects** (Asia Pacific University of Technology & Innovation). The theme required by the assignment is **flora / nature**.

The game must demonstrate:
- Sprite animation
- Particle effects
- Visual and audio special effects
- Event-driven gameplay
- At least two levels (we are building **four scenes**, one per group member)

The final deliverable is a fully playable game plus a ~5 minute demo video. This brief covers the **game code** only.

**Group:** 4 members. Each member owns **one scene** end-to-end (narrative, that scene's assets, that scene's code). Shared systems (core engine, UI, effects framework) are built collaboratively.

---

## 2. TECH STACK & CONVENTIONS

- **Language:** Python 3.10+
- **Engine:** Pygame (use `pygame` or `pygame-ce`; target 60 FPS)
- **Screen resolution:** 1280 x 720 (16:9). Define once in settings, never hard-code elsewhere.
- **Coding style:** Clear, beginner-friendly, well-commented. This is student code that must be understood and explained in an oral test, so favour readability over cleverness. Avoid advanced metaprogramming.
- **Paths:** Never hard-code file paths. Always build paths from a `BASE_DIR` defined in `config/settings.py` using `pathlib.Path`. See Section 8.
- **Asset loading:** All images/sounds load through a single `asset_loader.py`. Load once at scene start; never load inside the game loop.
- **No external assets committed blindly:** Every third-party asset must be creditable in the README (assignment requires crediting non-original work).

---

## 3. STORY & WORLD

**World name:** Aurelia — a large forest world kept alive for thousands of years by an ancient seed called the **Lumen Core**, buried deep underground, which radiates life energy so the plants grow huge and some are semi-alive.

**Inciting event:** A comet called the **Murk Comet** crashes into Aurelia. It cracks the ground, damages the Lumen Core, and releases a dark corrupting energy called the **Murk**. Plants twist into aggressive creatures; friendly creatures become enemies. The Lumen Core shatters into **four Lumen Shards**, scattered across four regions, each guarded by a corrupted guardian (a boss).

**Protagonist:** **Iris** — a young forest sprite, daughter of the last Keeper of the Lumen Core. Her father was injured in the crash. Iris must travel through four regions, collect all four Lumen Shards, defeat each corrupted guardian, and restore the Lumen Core before the Murk consumes Aurelia.

**Tone:** Whimsical but perilous; nature reclaiming hope. Each scene gets progressively harder and darker.

**Opening cutscene:** The main menu is always shown first on launch. Its "Start" option plays an 8-panel illustrated slideshow (`src/scenes/intro_scene.py`) telling the story above in captioned images — Ken Burns zoom per panel, crossfades between panels, cinematic letterbox bars, skippable at any time (ENTER/SPACE/click) — then continues straight into Scene 1. Panel art lives in `assets/images/opening_story/panel_1.png`..`panel_8.png`. Three panels carry one-shot sound cues timed to their captions: panel 3 ("a dark comet fell") plays `comet.wav`, panel 4 ("the Murk Comet struck") plays `burning_crater.wav`, and panel 6 ("the Murk began to spread") plays `titan_attack.wav` (layered 5x — see Scene 4's boss notes on why). The per-scene entries below "Start" remain a direct scene select that skips the cutscene, as before.

---

## 4. THE PLAYER — Iris

Iris is the only playable character. Health-based, life-based platforming.

### Abilities

| Ability | Key | Behaviour |
|---|---|---|
| **Glow Slash** | SPACE | Basic melee sword swing in a short arc in front of her. No cooldown. |
| **Pollen Burst** | Z | Releases a spore cloud in a circle around her, damaging nearby enemies. Short cooldown. Area-of-effect. |
| **Tendril Whip** | X | Fires a vine forward. Hits a surface → swing/grapple across a gap. Hits an enemy → pulls it toward her. Introduced and required in Scene 2. |
| **Lumen Bloom** (ultimate) | C | Unlocked after collecting the first Lumen Shard. Fires a ring of golden petals outward in all directions, stunning enemies hit. Long cooldown. |
| **Radiant Aura** | (automatic) | Triggers when Iris picks up a Glow Orb. Restores some HP with a green glow pulse. Not a button. |
| **Walk / Run** | Left / Right arrows | Constant-speed horizontal movement. |
| **Jump / Double Jump** | W or Up | Press once = jump; press again in air = smaller second jump. |
| **Crouch** | S or Down | Crouch to dodge high attacks / low ceilings. |

### Systems
- **Health:** Starts at 100 HP. Shown on a leaf-shaped HUD bar (top-left).
- **Lives:** Limited lives per playthrough. Losing all HP = lose one life, respawn at last checkpoint with full HP. No lives left = Game Over screen (restart current scene).
- **Checkpoints:** Glowing flower gates at the midpoint of each scene. Walking through saves progress.
- **Shard rewards:** Collecting Shard 1 unlocks Lumen Bloom. Later shards give small upgrades (e.g. max HP up, reduced cooldown). Keep these simple/optional.

---

## 5. SCENES (one per group member)

Each scene is a horizontal level ending in a boss and a Lumen Shard, EXCEPT the mechanics noted. Scene order = difficulty order.

### Scene 1 — The Glowcap Grotto  (Member 1)
- **Setting:** Underground cave lit by glowing blue-green mushrooms. Stalactites from the ceiling, mushroom-cap platforms from the floor. Three parallax background layers. Eerie, quiet.
- **Platforms:** Normal stone ledges + **mushroom-cap platforms that sink slightly when Iris stands on them** and rise back after she leaves.
- **Hazards:** **Acid pools** on the floor (constant damage while standing in them). Acid drips from stalactites later.
- **Enemies:** Murk Crawler (patrols). 
- **Mini-boss / Boss:** **Murk Crawler Elite** guards the sealed gate to the first Lumen Shard. (Implemented in code as **Jinn Monster** — a floating blue genie, ranged magic-orb vs. melee floor-slam depending on range — see `entities/enemies/jinn_monster.py`.)
- **Final boss:** Beyond Jinn Monster, a **breakable door** (3 Glow Slash/Pollen Burst hits) opens into a 20-tile arena added past the original level end, guarded by the **Bug Boss** (`entities/bosses/bug_boss.py`) — a hulking insectoid brute carrying a stick over one shoulder, styled after Hollow Knight's Husk Guard. Stays passive for Iris's first 3 tiles into the arena; crossing further wakes it and seals the door behind her until it dies. Alternates a ranged **Stomp** (a jagged white ground-shockwave, code-drawn, dodgeable only by jumping — `world/hazards.py`'s `GroundSpikeWave`) when Iris is at range, with a melee stick **Slam** (code-drawn dust burst on impact) when she's close. Displays a top-of-screen health bar once awake.
- **Key events:** Iris falls in from a crack above → tutorial (Glow Slash, movement) → cross sinking platforms over acid → checkpoint → defeat Murk Crawler Elite → gate opens → smash through the breakable door → defeat the Bug Boss → collect Lumen Shard 1.
- **Special effects:** Pollen Burst particle cloud (code), bioluminescent glow pulse on fungi (code, alpha), floor crack & collapse (tile state machine), player glow aura in dark zones, Bug Boss's ground-spike shockwave and slam dust cloud (both code-drawn, no image assets).

### Scene 2 — The Skybloom Reach  (Member 2)
- **Setting:** Jungle treetops high above ground. Wooden plank platforms on branches, connected by vines; some sway in the wind. Misty mountains in the far background. Bright then stormy near the boss.
- **Platforms:** Swaying wooden platforms; **Tendril Whip anchor points** to cross large gaps (falling = death, no floor to catch).
- **Hazards:** **Wind gust events** — strong wind pushes Iris sideways while debris streams across the screen.
- **Enemies:** **Briarling** (runs fast, attacks with a club / fires projectile), **Stalker Root** (hides underground, ambushes, briefly grabs Iris).
- **Boss:** **Sky Wisp** (a dragon). Phase 1: flies and dives. Phase 2 (after enough damage): faster, dives more, summons Briarlings when it roars.
- **Key events:** Emerge from vine shaft → fight Briarlings → first Tendril Whip gap (tutorial) → Stalker Root ambush → wind gust event → checkpoint → second Tendril Whip section → Sky Wisp fight → collect Lumen Shard 2.
- **Special effects:** Wind gust particles (code spawns leaf sprites), Tendril Whip rope (code lines), Sky Wisp feather rain on death (code spawns feather sprites), soil burst on Stalker Root emerge.

### Scene 3 — The Hollow Spire  (Member 3)
- **Setting:** Corrupted fortress overtaken by fungus. Stone walls with glowing purple/orange mycelium veins. Narrow corridors, low ceilings. Tense, oppressive.
- **Platforms:** Stone floor tiles; wall ledges in a vertical shaft section.
- **Hazards:** **Murk pools** (instant damage on contact), **mycelium tendrils** that shoot across corridors on a timer (moving barriers), and the **Murk Meter** — an HUD bar that fills over time; if full, Iris takes passive damage until she destroys a **Murk Spore cluster** (glowing growth on walls) to reduce it.
- **Enemies:** Murk Crawlers (respawn once).
- **Puzzle:** Three **vine switches** hidden in side corridors; hitting all three opens the boss gate.
- **Boss:** **Fungal Warden** (a tall hooded figure). Phase 1: walks and ground-slams (triggers floor fracture). Phase 2: stationary, rains spores from above, wider slam.
- **Key events:** Enter, doors seal shut → corridor + tendril trap → destroy Murk Spore clusters → vertical shaft climb → three-switch puzzle → checkpoint → Fungal Warden two-phase fight → collect Lumen Shard 3.
- **Special effects:** Bioluminescent pulse (code alpha), shockwave ring on slam (code circle), spore rain (code spawns spore sprites), screen shake (camera offset), Murk pool ripple.

### Scene 4 — The Last Radiance  (Member 4)
- **Setting:** The **Lumen Core Chamber** — a large **circular, non-scrolling arena** directly above the broken Lumen Core. Cracked crystal floor. The background has TWO versions: **corrupted** (dark, red cracks, dead vines) and **restored** (golden light, blooming flowers). The corrupted version shows for the entire fight; it is a **hard switch to fully restored**, not a gradual HP-tied crossfade, timed to the moment the purification white-fade lifts after the boss is defeated (see Key events below).
- **Platforms:** Six fixed crystal ledges at varying heights across the arena. No gaps (crystal floor covers full width). Comet impacts and root-cage eruptions leave **burning crater** hazard tiles plus a permanent scorch mark baked into a dedicated decal layer, so ground damage visibly accumulates across the fight — the decals themselves burn away the moment the land is purified.
- **Hazards:** **Root cages** (trap Iris briefly, break out by mashing movement), **petal barrage** (homing petals, deflectable with Glow Slash), **comet drops** (fall from top, explode, leave burning craters).
- **Boss:** **Aurelian Titan** (a giant tree/root creature). Three phases: P1 root cages; P2 petal barrage + comet drops; P3 all attacks combined, moves faster, sprite scaled up ~1.2x in code. Every attack telegraphs through the same shared cast animation, with the actual effect (root cage / petals / comet) firing partway through that windup rather than at its start.
- **Key events:** Opening **flashback cutscene** (comet sprite falls and impacts the Core, screen fully black with HUD hidden) → the instant the cutscene ends, the Titan becomes visible with its own reveal effect and a stronger screen shake → three-phase Aurelian Titan fight (arena background stays corrupted throughout) → on defeat, gameplay freezes for the Titan's death animation, then a golden purification burst expands from its position and crossfades to a white screen and back, revealing the restored background and ledges → final Lumen Shard spawns to collect → victory screen with completion time + token count.
- **Special effects:**
  - **Opening cutscene:** comet sprite falling with a trailing ember particle stream, an expanding shockwave ring plus explosion burst and screen shake on impact, and a scorch decal left where it lands; the player HUD is hidden for the whole cutscene so nothing else is on screen.
  - **Titan reveal:** on first becoming visible, the boss fades in from a dark silhouette (backlit by an additive orange glow) into full colour, with a brief punch-in scale overshoot for extra weight, paired with the fight's strongest screen shake.
  - **Idle ambient embers:** small motes continuously drift up off the Titan between attacks so it never reads as static.
  - **Attack telegraph:** a pulsing red glow along all four screen edges for the boss's entire windup (roar to impact), giving a readable "attack incoming" cue before root cage / petal barrage / comet drops actually land.
  - **Root cage snare** (vine sprite trap) and **petal barrage** (code-spawned homing petals, deflectable with Glow Slash) as before.
  - **Purification sequence:** procedural golden radial-gradient burst (additive blend, no dedicated art asset) expanding from the boss on defeat, crossfading into a white screen and back; background then hard-switches from corrupted to restored art.
  - **Blight Meter danger vignette** fades in once the meter passes half-full, same as Scene 3's Murk Meter.

---

## 6. ENEMIES & BOSSES — CANONICAL REFERENCE

> **IMPORTANT:** These name→appearance mappings are final and were corrected by the team. Do not infer appearance from the name alone.

| Name | Type | Scene | Appearance |
|---|---|---|---|
| Murk Crawler | Regular | 1 | Mushroom creature, purple cap, glowing red eyes |
| Murk Crawler Elite | Mini-boss | 1 | Larger tougher Murk Crawler; fires spore projectiles (implemented as Jinn Monster, a floating blue genie) |
| Bug Boss | Final Boss | 1 | Hulking insectoid brute carrying a stick over one shoulder |
| Briarling | Regular | 2 | Horned grey creature carrying a wooden club |
| Stalker Root | Regular | 2 | Mossy stone-golem creature that emerges from the ground |
| Sky Wisp | Boss | 2 | **A dragon** (purple/gold, winged) |
| Fungal Warden | Boss | 3 | **A tall hooded figure** in an earthy cloak, glowing eyes |
| Aurelian Titan | Final Boss | 4 | **A giant tree/root creature** with bark body and leaves |

### Event-driven behaviours (apply across scenes)
- Enemy HP reaches 0 → death animation + particle burst + drop item (if any) spawns + sprite removed.
- Boss HP reaches ~50% → enter next phase: background shifts, attack pattern changes, music intensifies.
- Floor fracture (Scene 1 & 3): boss slam cracks nearby floor tiles → after ~2s they break and Iris falls through.
- Murk Meter full (Scene 3 & 4) → passive damage + dark vignette + ambient hum until a Murk Spore cluster is destroyed.
- Iris HP reaches 0 → death animation → lose a life → respawn at checkpoint (or Game Over if no lives).
- Scene complete → wipe transition + narrative text card → next scene unlocked.

---

## 7. COLLECTIBLES

- **Glow Orb** — restores HP, triggers Radiant Aura. Dropped by enemies or placed in level.
- **Coin** — cosmetic, counted on the results screen.
- **Lumen Shard** — one per scene, behind the boss/puzzle. Collecting saves progress and unlocks the next scene.
- **Lumen Token** — hidden collectible for exploration; collecting all in a scene can unlock a bonus.

---

## 8. FOLDER / FILE STRUCTURE

Create exactly this structure. Each `.py` file's purpose is noted.

```
LumenBloom/
├── main.py                     # Entry point: creates Game() and runs it
├── requirements.txt            # pygame (or pygame-ce)
├── README.md                   # How to run, controls, asset credits
├── PROJECT_BRIEF.md            # This file — keep it in the repo
│
├── config/
│   └── settings.py             # BASE_DIR + all paths, SCREEN_W/H, FPS, COLORS, key bindings, gameplay constants
│
├── src/
│   ├── core/
│   │   ├── game.py             # Main loop, clock, screen, delta time
│   │   ├── scene_manager.py    # Holds current scene; switches menu <-> scenes 1-4
│   │   ├── camera.py           # Horizontal scroll + screen-shake offset
│   │   └── asset_loader.py     # load_image(), load_sound(), sprite-sheet slicing, caching
│   │
│   ├── entities/
│   │   ├── player.py           # Iris: input, movement, jump/double-jump, abilities, animation state machine, HP/lives
│   │   ├── enemy.py            # Base Enemy class: HP, patrol, contact damage, death
│   │   ├── projectile.py       # Spore/thorn projectiles
│   │   ├── enemies/
│   │   │   ├── murk_crawler.py
│   │   │   ├── briarling.py
│   │   │   └── stalker_root.py
│   │   └── bosses/
│   │       ├── boss_base.py     # Shared boss logic: phases, health bar, phase transitions
│   │       ├── bug_boss.py      # Scene 1's final boss, beyond the breakable door past Jinn Monster
│   │       ├── sky_wisp.py
│   │       ├── fungal_warden.py
│   │       └── aurelian_titan.py
│   │
│   ├── effects/
│   │   ├── particles.py         # Generic particle system: Pollen Burst, spore rain, wind leaves, soil, petals, feathers
│   │   ├── shockwave.py         # Expanding ring (code-drawn)
│   │   ├── glow.py              # Pulsing alpha glow (fungi, Radiant Aura) using a glow overlay image
│   │   └── transitions.py       # Screen flash, wipe transition, Scene-4 background crossfade, screen shake helper
│   │
│   ├── world/
│   │   ├── tilemap.py           # Load tileset, build level from a tile grid, collision, floor-fracture tile states
│   │   ├── platforms.py         # Moving/sinking/swaying platforms
│   │   ├── collectibles.py      # Glow Orb, coin, Lumen Shard, Lumen Token, checkpoint gate
│   │   └── hazards.py           # Acid pool, Murk pool, mycelium tendril, Murk Spore cluster, burning crater
│   │
│   ├── ui/
│   │   ├── hud.py               # HP bar, lives, ability cooldown icons, Murk Meter
│   │   └── menus.py             # Main menu, pause, Game Over, Victory, scene-transition text cards
│   │
│   └── scenes/
│       ├── base_scene.py        # Shared scene lifecycle: handle_events(), update(), draw(); loads bg layers, tilemap, entities
│       ├── scene1_grotto.py     # Member 1
│       ├── scene2_skybloom.py   # Member 2
│       ├── scene3_spire.py      # Member 3
│       ├── scene4_radiance.py   # Member 4
│       └── intro_scene.py       # Opening 8-panel story slideshow, played once before the main menu
│
└── assets/
    ├── images/
    │   ├── player/
    │   ├── enemies/
    │   ├── bosses/
    │   ├── backgrounds/
    │   │   ├── scene1/  scene2/  scene3/  scene4/
    │   ├── tiles/
    │   ├── hazards/
    │   ├── objects/
    │   ├── effects/
    │   ├── ui/
    │   └── opening_story/        # panel_1.png .. panel_8.png — opening cutscene art
    └── audio/
        ├── music/
        └── sfx/
```

---

## 9. COMPLETE ASSET FILENAME LIST

> The code must expect **exactly these filenames**. If a file is missing, fail gracefully with a clear console message (e.g. `print("MISSING: assets/images/player/iris_run.png")`) and, where reasonable, fall back to a coloured placeholder rectangle so development can continue before all art is ready.

**Animation convention:** each sprite sheet is a single horizontal row of equally-sized frames on a transparent background, facing right. The loader slices by frame count. If a sheet comes with a non-transparent background, note it and use a colour-key in the loader.

### Player — `assets/images/player/`
`iris_idle.png` (4), `iris_run.png` (6-8), `iris_jump.png` (2-3), `iris_fall.png` (2), `iris_double_jump.png` (3), `iris_crouch.png` (2), `iris_attack.png` (4), `iris_pollen_burst.png` (3-4), `iris_tendril_whip.png` (3-4), `iris_hurt.png` (2), `iris_death.png` (5)

### Enemies — `assets/images/enemies/`
`murk_crawler_walk.png` (4), `murk_crawler_death.png` (3),
`murk_crawler_elite_idle.png` (2), `murk_crawler_elite_attack.png` (3), `murk_crawler_elite_death.png` (5),
`briarling_run.png` (5), `briarling_attack.png` (3), `briarling_death.png` (3),
`stalker_root_emerge.png` (5), `stalker_root_grab.png` (3), `stalker_root_retreat.png` (5),
`spore_projectile.png` (2), `thorn_projectile.png` (1-2)

### Bosses — `assets/images/bosses/`
`sky_wisp_fly.png` (6), `sky_wisp_dive.png` (4), `sky_wisp_roar.png` (4), `sky_wisp_hurt.png` (2), `sky_wisp_death.png` (6),
`fungal_warden_walk.png` (4), `fungal_warden_slam.png` (5), `fungal_warden_spore_rain.png` (3), `fungal_warden_hurt.png` (2), `fungal_warden_death.png` (7),
`aurelian_titan_idle.png` (3), `aurelian_titan_attack.png` (4), `aurelian_titan_slam.png` (4), `aurelian_titan_hurt.png` (2), `aurelian_titan_death.png` (6),
`bug_boss_idle.png` (4), `bug_boss_stomp.png` (6), `bug_boss_slam.png` (6), `bug_boss_hurt.png` (2), `bug_boss_death.png` (6) — 160x160 canvas, not yet sourced (renders as a placeholder rectangle until added)

### Backgrounds — `assets/images/backgrounds/`
- `scene1/layer1_far.png`, `scene1/layer2_mid.png`, `scene1/layer3_near.png`
- `scene2/layer1_far.png`, `scene2/layer2_mid.png`, `scene2/layer3_near.png`
- `scene3/layer1_far.png`, `scene3/layer2_near.png`
- `scene4/corrupted.png`, `scene4/restored.png`

### Tiles / platforms — `assets/images/tiles/`
`grotto_tileset.png`, `skybloom_tileset.png`, `spire_tileset.png`, `radiance_tileset.png`,
`mushroom_platform.png` (1-2), `swaying_platform.png` (1), `crystal_ledge.png` (1)
> Each tileset sheet must include: solid tile, edge/corner variants, and a cracked/broken variant for floor fracture.

### Hazards — `assets/images/hazards/`
`acid_pool.png` (3-4, tileable), `murk_pool.png` (3-4), `mycelium_tendril.png` (3), `murk_spore_cluster.png` (2), `burning_crater.png` (2)

### Objects — `assets/images/objects/`
`lumen_shard.png` (4), `glow_orb.png` (4), `coin.png` (4), `lumen_token.png` (4), `checkpoint_gate.png` (4, inactive+active), `vine_switch.png` (2, off/on), `boss_gate.png` (1)

### Effects — `assets/images/effects/`
`explosion.png` (5-6), `comet.png` (1), `petal.png` (1), `feather.png` (1), `glow_overlay.png` (1, soft radial gradient, transparent edges), `wind_leaf.png` (1), `soil_particle.png` (1)
> Pure-code effects (NO image needed): Pollen Burst cloud, shockwave ring, Tendril Whip rope, screen shake, background crossfade, bioluminescent pulse.

### UI — `assets/images/ui/`
`hp_bar_full.png`, `hp_bar_75.png`, `hp_bar_50.png`, `hp_bar_25.png`, `hp_bar_empty.png` (or one sheet), `life_icon.png`, `icon_pollen_burst.png`, `icon_tendril_whip.png`, `icon_lumen_bloom.png`, `murk_meter.png`, `title_logo.png`

### Audio — `assets/audio/`
- `music/`: `menu_theme.ogg`, `intro_theme.ogg`, `scene1_theme.ogg`, `scene2_theme.ogg`, `scene3_theme.ogg`, `scene4_theme.ogg`, `victory_theme.ogg`, `game_over_theme.ogg` (filenames as actually used by `scene_manager.py`; older than this doc)
- `sfx/`: `glow_slash.wav`, `pollen_burst.wav`, `tendril_whip.wav`, `lumen_bloom.wav`, `radiant_aura.wav`, `shard_collect.wav`, `checkpoint.wav`, `enemy_hurt.wav`, `iris_hurt.wav`, `iris_death.wav`, `slam.wav`, `shockwave.wav`, `comet_impact.wav`, `murk_warning.wav`

---

## 10. BUILD ORDER (recommended for Claude Code)

Build and TEST each step before moving on. Get a running window first; add features incrementally.

1. **Skeleton:** `settings.py`, `asset_loader.py` (with placeholder-rectangle fallback), `game.py`, `main.py` → a 1280x720 window at 60 FPS that opens and closes cleanly.
2. **Player basics:** `player.py` — Iris idle/run/jump/double-jump/crouch on a flat test floor, with animation. Placeholder rectangle if `iris_*.png` missing.
3. **World:** `tilemap.py` + `platforms.py` — build one test level with solid + sinking platforms and collision.
4. **Combat:** `enemy.py` + `murk_crawler.py` + Glow Slash + Pollen Burst; enemy takes damage and dies.
5. **HUD:** `hud.py` — HP bar, lives, cooldown icons.
6. **Effects framework:** `particles.py`, `shockwave.py`, `glow.py`, `transitions.py`.
7. **Scene 1 full:** wire `scene1_grotto.py` — hazards (acid), checkpoint, Murk Crawler Elite mini-boss, Lumen Shard, scene-complete transition.
8. **Scene manager + menus:** `scene_manager.py`, `menus.py` — main menu → Scene 1 → transition.
9. **Replicate for Scenes 2-4:** each member builds their scene file using Scene 1 as the template; add their enemies/boss/hazards.
10. **Audio + polish:** background music per scene, SFX hooks on events, final balancing.

---

## 11. GROUP WORKLOAD MAPPING

| Member | Owns | Files |
|---|---|---|
| Member 1 | Scene 1 (Glowcap Grotto) | `scenes/scene1_grotto.py`, `enemies/murk_crawler.py` |
| Member 2 | Scene 2 (Skybloom Reach) | `scenes/scene2_skybloom.py`, `enemies/briarling.py`, `enemies/stalker_root.py`, `bosses/sky_wisp.py` |
| Member 3 | Scene 3 (Hollow Spire) | `scenes/scene3_spire.py`, `bosses/fungal_warden.py` |
| Member 4 | Scene 4 (Last Radiance) | `scenes/scene4_radiance.py`, `bosses/aurelian_titan.py`, demo video editing |
| All | Core engine, effects, UI, player, testing, audio | `core/`, `effects/`, `ui/`, `entities/player.py` |

---

## 12. GUARDRAILS FOR CLAUDE CODE

- Keep the four scenes structurally consistent — they should all subclass `base_scene.py` and follow the same lifecycle, so each member's scene plugs in the same way.
- Do not invent new characters, abilities, or lore. Use Section 3-7 exactly.
- Respect the canonical enemy appearances in Section 6 (Sky Wisp = dragon, Fungal Warden = hooded, Aurelian Titan = tree).
- Missing assets must not crash the game — use labelled placeholder rectangles and a console warning, so the team can code before all art is finished.
- Comment code clearly; each member must be able to explain their scene in an oral test.
- This is a learning artefact: prefer simple, explicit, readable Pygame patterns over heavy abstraction.
