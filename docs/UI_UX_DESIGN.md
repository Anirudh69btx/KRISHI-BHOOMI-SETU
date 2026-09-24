UI/UX Design Specification
Theme: "Earth & Sky, Instrumented" — Soil Ochre · Leaf Green · Monsoon Sky · Signal Lime Platform: Farmer PWA (Android-first) · Expert / FPO / Government Studio (desktop) · flip.farm (public site) Standard: WCAG 2.1 AA, with AAA on all decision-critical and emergency surfaces Supersedes: v3.0. See §16 for the changelog and migration notes.

0. What changed in v4.0, and why
v3.0 defined a correct, humane, accessible system. It did not define a memorable one. It could have belonged to any agri-tech product.

v4.0 keeps every v3.0 constraint — 72dp targets, offline-first, WCAG AA, ten languages — and adds a visual point of view: FLIP looks like a scientific instrument pointed at a real field, not like a dashboard template.

The temptation was to adopt the premium agri-tech look wholesale: dark glass panels floating over satellite imagery, acid-lime accents, cinematic photography, scroll-linked motion. That look is built for a colour-calibrated laptop in an office. FLIP's primary user holds a ₹6,000–10,000 Android phone in direct 100,000-lux sunlight, with wet or muddy hands, on a 2G connection, and may not read fluently.

Applying that aesthetic directly to the Farmer PWA would have produced a beautiful product that is unusable in a field.

So v4.0 resolves it with a Two-Tier Surface Doctrine (§2): one shared design DNA, two hardening levels. The cinematic language lives fully in the Studio and public site. The Farmer PWA inherits the same palette, geometry, type scale and data-visualisation language — but hardened for sunlight, low-end silicon, and low literacy.

Both tiers are visibly the same product. Only one of them is allowed to be pretty at the expense of being readable.

1. Design Philosophy
       ┌──────────────────────────────────────────────────────────────────────┐
       │                        FLIP UI/UX PILLARS                            │
       ├───────────────┬───────────────┬────────────────┬─────────────────────┤
       │ FARMER-FIRST  │ OFFLINE-FIRST │ TRUST-BUILDING │ INSTRUMENT-GRADE    │
       │ • Voice-first │ • Zero        │ • Transparent  │ • Data is the hero  │
       │ • Zero-typing │   loaders     │   "WHY"        │ • Real imagery, not │
       │ • Low-        │ • Stale-      │ • Conformal    │   illustration      │
       │   literacy    │   while-      │   bounds       │ • Pattern-coded,    │
       │ • 72dp        │   revalidate  │ • Visible      │   not colour-coded  │
       │   targets     │ • CRDT merge  │   expert queue │ • Rationed accent   │
       └───────────────┴───────────────┴────────────────┴─────────────────────┘
1.1 Farmer-First
Designed for rural smallholders who may have limited textual literacy. Audio cues, unambiguous pictograms, pattern-and-colour-coded status, and spoken natural-language interaction replace text-heavy input. Touch targets are a minimum of 72dp for primary actions, sized for one-handed operation with wet hands.

1.2 Offline-First
No blocking spinner, ever. Cached data renders on first paint. Pending actions show a local confirmation state immediately and carry a sync badge until the CRDT merge resolves. An offline screen is a fully working screen with a status strip, not an error page.

1.3 Trust & Transparency
Farmers do not act on black-box advice. Every advisory decomposes into four named blocks, and this vocabulary never changes anywhere in the product:

Block	Job	Visual weight
NOW	The one immediate, non-negotiable step	Heaviest — largest type in the card
NEXT	What to expect in 24–48 hours	Quiet, secondary
WHY	The observable sensor or weather cause	Body copy with tappable evidence chips
CONFIDENCE	Statistical certainty + expert review status	Coverage bar, never a bare percentage
1.4 Instrument-Grade Aesthetic ("Earth & Sky, Instrumented")
Grounded in the real materials of Indian smallholder farming — wet soil, chlorophyll, monsoon sky, terracotta — and presented with the discipline of a measuring instrument: numbers set large, labels set small and quiet, one action colour used sparingly, real photography instead of vector illustration, and texture used to carry meaning rather than decorate.

The governing restraint: boldness is spent in exactly one place per screen. On the Farmer Dashboard that place is the farm itself. Everything around it stays quiet.

2. The Two-Tier Surface Doctrine
This is the structural decision that governs every token below.

  ┌─────────────────────── SHARED TOKEN SPINE ───────────────────────┐
  │  palette · type scale · radius law · spacing · data-viz language │
  │  pictogram set · motion curves · copy voice                      │
  └──────────────┬─────────────────────────────────┬─────────────────┘
                 │                                 │
      ┌──────────▼──────────┐           ┌──────────▼──────────┐
      │   TIER A — FIELD    │           │  TIER B — STUDIO    │
      │   Farmer PWA        │           │  Expert / FPO /     │
      │                     │           │  Govt / flip.farm   │
      ├─────────────────────┤           ├─────────────────────┤
      │ Sunlight-readable   │           │ Indoor, calibrated  │
      │ Solid surfaces      │           │ Glass + blur        │
      │ Contrast ≥ 7:1      │           │ Contrast ≥ 4.5:1    │
      │ 72dp targets        │           │ 44px targets        │
      │ Blur ≤ 8px, gated   │           │ Blur 24–32px        │
      │ Motion ≤ 200ms      │           │ Scroll-linked       │
      │ ≤ 180KB initial JS  │           │ Budget relaxed      │
      │ One accent per view │           │ One accent per      │
      │                     │           │ region              │
      └─────────────────────┘           └─────────────────────┘
2.1 The borrowing rule
A Tier A screen may borrow Tier B's cinematic treatment only in ambient regions — the dashboard header over farm imagery, the 3D farm canvas, the onboarding welcome sequence.

It may never borrow it in a decision-critical region: advisory cards, dosage figures, confidence readouts, emergency banners, and any control that commits an action. Those regions are solid-surface, maximum-contrast, pictogram-labelled, always.

2.2 The single-product test
Put a Farmer PWA screenshot next to an Expert Studio screenshot. A stranger must identify them as the same product within two seconds — from palette, geometry, and the shape of the data — without either screen having compromised its own job.

3. Design System Tokens
3.1 Colour palette
action accent

canvas ground

Leaf

leaf-900 : #16351C

leaf-700 : #2E7D32

leaf-500 : #4CAF50

leaf-100 : #E8F5E9

Signal

lime-400 : #D4F25A

lime-600 : #A8C93F

Sky

sky-700 : #1565C0

sky-400 : #42A5F5

sky-100 : #E3F2FD

Earth

soil-500 : #8D6E63

terracotta : #D84315

humus-900 : #3E2723

humus-950 : #0B1E12

Core spine (both tiers)
/* Leaf — brand identity, "healthy / verified / optimal" */
--leaf-950: #0F2614;
--leaf-900: #16351C;   /* deepest usable green surface     */
--leaf-800: #1E4A26;   /* raised dark surface              */
--leaf-700: #2E7D32;   /* BRAND PRIMARY (carried from v3)  */
--leaf-500: #4CAF50;
--leaf-300: #81C784;   /* brand primary on dark tier       */
--leaf-100: #E8F5E9;

/* Signal — the action accent. New in v4. */
--lime-400: #D4F25A;   /* primary CTA, active voice state  */
--lime-600: #A8C93F;   /* hover / pressed                  */

/* Sky — water, irrigation, forecast, information */
--sky-700:  #1565C0;
--sky-400:  #42A5F5;
--sky-100:  #E3F2FD;

/* Earth — soil, canvas grounds, nutrient data */
--soil-500:   #8D6E63;
--soil-300:   #BCAAA4;
--humus-900:  #3E2723;
--humus-950:  #0B1E12;  /* deepest canvas, Studio tier     */

/* Surfaces */
--bone-50:  #F4F3EC;   /* warm canvas — replaces #FAFAFA   */
--paper:    #FFFFFF;   /* card surface, Field tier          */
--tint-leaf:#F1F8E9;
--dark-canvas: #121212;
--dark-card:   #1E1E1E;
--dark-tint:   #1B2E1D;

/* Text */
--ink-900: #0E2015;    /* primary text on light             */
--ink-600: #5C6B60;    /* labels, captions on light         */
--ink-inv: #F4F3EC;    /* text on dark                      */
--ink-inv-muted: rgba(244,243,236,0.58);
Status — tier-paired
Status colours must be brightened on dark surfaces. A v3.0 mistake worth naming: #C62828 on #121212 reads at 3.1:1 and fails.

Meaning	Light tier	Dark tier	Pictogram	Pattern
Critical / Emergency	#C62828	#FF6B5E	Filled triangle	Cross-hatch
Warning / Vigilance	#EF6C00	#FFA726	Hollow triangle	Dot matrix
Optimal / Verified	#2E7D32	#81C784	Circle with tick	45° stripes
Information	#0288D1	#4FC3F7	Circle with i	Solid
No data / Stale	#8D6E63	#BCAAA4	Dashed circle	Dashed outline
Every status is encoded three times: colour, pictogram, pattern. This satisfies the colourblind-safe requirement from v3.0 §5 without adding any text, which matters for low-literacy users.

Accent discipline — non-negotiable
Lime means "you can act on this." Primary CTA, active voice state, the single highlighted metric. Nothing else.
Lime is never a status colour. --leaf-700 already owns "optimal." Using lime for "healthy" would collide with "actionable" and destroy the signal.
Lime covers under 5% of any viewport. One lime element per screen region. Two lime buttons side by side is a defect.
Never white or light text on lime — #FFFFFF on #D4F25A is 1.5:1. Text on lime is always --ink-900 (12.4:1).
Terracotta #D84315 and soil tones appear in nutrient and soil data visualisation only — never on controls, never on text.
No purple. No blue gradients. Gradients are permitted only as tonal fades within a single hue, or as image scrims.
Glass tokens (Tier B; gated on Tier A — see §3.6)
--glass-dark:  rgba(11,30,18,0.55);   /* + backdrop-filter: blur(32px) saturate(130%) */
--glass-light: rgba(244,243,236,0.82); /* + backdrop-filter: blur(24px)               */
--glass-edge:  inset 0 1px 0 rgba(255,255,255,0.14),
               inset 1px 0 0 rgba(255,255,255,0.08);
Every translucent panel carries --glass-edge. Blur without a lit top-left edge reads as a rendering bug, not as glass. There are no exceptions.

3.2 Typography
Families
Role	Family	Where
Workhorse (all scripts)	Inter Variable 100–900	Everywhere
Indic scripts	Noto Sans per script, subsetted	Everywhere
Display (Latin only)	General Sans 500–700	Tier B + flip.farm only
Inter stays the workhorse because it is variable (one file, all weights — critical on 2G) and its Latin metrics sit close to Noto Sans, so mixed-script lines do not jump.

General Sans is added for Tier B display sizes only, where its tighter apertures and geometric caps carry the instrument personality that Inter at 64px does not. It is never loaded on the Farmer PWA — that would cost ~40KB for zero functional gain.

Indic script coverage, dynamically loaded (§11): Devanagari (hi, mr) · Telugu (te) · Kannada (kn) · Gujarati (gu) · Gurmukhi (pa) · Bengali & Assamese (bn, as) · Odia (or)

Scale
Token	Size / line-height / tracking / weight	Use
display-xl	96 / 0.92 / −0.035em / 600	flip.farm hero only
display-l	64 / 0.96 / −0.03em / 600	Studio chapter openers
display-m	32 / 1.25 / −0.01em / 600	Farmer greeting, emergency headline
title-l	24 / 1.3 / −0.01em / 600	Advisory card title
title-m	20 / 1.4 / 0 / 500	Card headers, the NOW line
metric-xl	56 / 1.0 / −0.03em / 600	Studio hero KPI
metric-l	36 / 1.0 / −0.025em / 500	Sensor card value
metric-m	24 / 1.0 / −0.02em / 500	Stat pill value
body-l	18 / 1.55 / 0 / 400	Advisory description, WHY block
body	16 / 1.6 / 0 / 400	Standard copy — Field tier floor
label	14 / 1.45 / 0 / 600	Buttons, tags, field labels
caption	13 / 1.4 / 0 / 400	Timestamps, units — Indic floor
micro	11 / 1.2 / +0.04em / 500	Coordinates, meta — Latin only
Script-specific rules
These are correctness requirements, not preferences:

Devanagari, Bengali, Gurmukhi, Odia carry matras above and below the baseline. Add +0.15 to line-height over the Latin value. body in Hindi is 16/1.75, not 16/1.6.
Minimum size for Indic scripts is 16px for body and 13px for captions. The micro token is Latin-only. An 11px Devanagari string loses its matras on a 720p screen.
Telugu and Kannada have taller ascenders — cap their containers at 1.9 line-height to prevent overflow in fixed-height cards.
Never letter-space Indic text. Conjuncts break.
General type rules
font-variant-numeric: tabular-nums on every element that displays data. A sensor value must not reflow the card when it ticks from 9% to 10%.
The metric-to-label size ratio is always 3:1 or greater. The number shouts; the label whispers at --ink-600.
Maximum measure: 62 characters for body, 48 for lead paragraphs.
Sentence case throughout. No ALL-CAPS labels — they slow reading for low-literacy users and are illegible in Indic scripts.
Headlines break across lines manually (top line longer). Never allow an orphan.
3.3 Spacing, targets, and layout
Base unit: 8px. Scale: 4 · 8 · 16 · 24 · 32 · 48 · 64 · 96 · 128 · 160.
Touch targets: 72dp minimum for every primary action on Tier A. 56dp for secondary. 44px on Tier B.
Minimum gap between adjacent touch targets: 12dp. Mud-and-glove operation is the design condition.
Thumb zone: on Tier A, all primary actions sit in the bottom 45% of the viewport. The top 20% is read-only.
Grid: Tier A is a single column, 20px margins. Tier B is 12 columns, 1280px max container, 24px gutter, 80px outer margin.
Section rhythm: Tier A 32px, Tier B 160px desktop / 96px tablet.
3.4 Radius system and the nesting law
--r-xs:   8px;   /* chips, icon tiles                    */
--r-sm:  12px;   /* inputs, small cards                  */
--r-md:  16px;   /* Tier A card default (carried from v3)*/
--r-lg:  24px;   /* Tier B card default                  */
--r-xl:  32px;   /* hero panels, floating rails          */
--r-full: 999px; /* pills, avatars, toggles, FABs        */
The nesting law: inner radius = outer radius − inner padding.

A 24px card with 8px padding contains 16px children. A 16px card with 8px padding contains 8px children. Applying one radius to every element regardless of nesting is the single most visible amateur tell in the system, and v3.0's flat "16px everywhere" rule is replaced by this.

3.5 Elevation
Shadows are wide, soft, and nearly invisible. Never dark, never tight.

--e1: 0 1px 2px  rgba(11,30,18,0.04);
--e2: 0 4px 16px rgba(11,30,18,0.06);
--e3: 0 12px 40px rgba(11,30,18,0.10);
--e4: 0 24px 80px rgba(11,30,18,0.14);  /* floating HUD over imagery */
Tier A cards use --e1 plus a 1px rgba(14,32,21,0.06) border. Tier B glass panels use --e3 plus --glass-edge.

3.6 The glass performance gate
backdrop-filter is the most expensive property in this system. On a 2GB-RAM Android device it can cost 20–40ms per frame, which turns a scroll into a slideshow. It is therefore capability-gated, not stylistic.

// Resolved once at boot, written to a data-attribute on <html>
const tier =
  navigator.connection?.saveData          ? 'flat'  :
  (navigator.deviceMemory ?? 1) < 2       ? 'flat'  :
  (navigator.deviceMemory ?? 1) < 4       ? 'light' : 'full';
Tier	backdrop-filter	Fallback
full	blur 24–32px	—
light	blur 8px, static regions only	—
flat	none	Solid --bone-50 / --leaf-900 at 100% opacity
Hard rules:

Blur is never applied behind a scrolling list.
Blur covers no more than 30% of the viewport on Tier A.
The emergency banner is never glass. It is a solid surface at maximum contrast in all tiers.
Every glass surface must remain legible when its blur is removed. Design the flat fallback first, then add blur.
4. Motion System
--ease-out:   cubic-bezier(0.22, 1, 0.36, 1);   /* entrances, reveals */
--ease-micro: cubic-bezier(0.4, 0, 0.2, 1);     /* hover, press       */
Scope	Tier A	Tier B
Micro (press, toggle)	160ms	200ms
Component (card, sheet)	240ms	400ms
Section / scene	320ms	700–1200ms
Rules
Tier B uses scroll-linked motion, not scroll-triggered. Scroll progress drives transforms continuously, so the page behaves like a mechanism. Lenis, lerp 0.08.
Tier A uses response motion only. Motion answers a tap — a sheet opening, a value committing, a sync resolving. There is no ambient or decorative animation on the Farmer PWA. Battery and frame budget are the reason, and it also happens to be better design.
Metric count-up on first view, 900ms, tabular figures so nothing reflows. Tier B only.
One orchestrated moment per screen. The Farmer Dashboard's moment is the farm canvas settling into place on load. Nothing else animates unprompted.
prefers-reduced-motion: reduce replaces every transform with a 200ms opacity change. The 3D farm canvas drops to a static orthographic render with tappable field polygons — full functionality, zero camera movement.
Device-tier throttle, independent of the user preference: at flat tier, the 3D canvas serves the same static render and all section transitions become instant.
The emergency pulse (§7.5) is the sole exception to reduced-motion, degraded to a 2s opacity cycle rather than removed, because it is a safety signal. Audio and haptics carry the alert regardless.
5. Data Visualisation Language
5.1 Pattern-first encoding
Charts use SVG pattern fills, not solid colour. In most products this is a stylistic choice. In FLIP it is the accessibility mechanism — it delivers the v3.0 requirement that "no status is communicated exclusively via colour" without adding text.

P1  ▨ 45° stripes     → Optimal / healthy
P2  ⁘ dot matrix      → Caution / watch
P3  ▩ cross-hatch     → Critical / act now
P4  ░ dashed outline  → No data / stale reading
Define these once as <pattern> defs and reference them everywhere: donut segments, map polygons, progress fills, legend swatches.

5.2 Chart rules
Arc / donut: stroke-only, 24–32px thick, rounded caps, visible gaps between segments, each segment a distinct pattern. Used for leaf-area index and nutrient balance.
Sparkline (24h sensor trend): 1.5px stroke, no grid, no axes, optional 6%-opacity fade fill, a floating tooltip pill on touch. Below it, a 3px quality-flag bar segmented by reading confidence — solid where the sensor was healthy, dashed where readings were interpolated.
Progress track: 4px, --r-full, rail rgba(ink,0.08), fill --ink-900. Not lime — lime is reserved for actions.
Field heatmap: continuous --leaf-500 → --warn → --alert ramp over the map polygon, pattern-overlaid, with a labelled gradient legend bar beneath running Very Low → Very High, plus a 12-month scrub track for temporal comparison.
Contour lines: 1px rgba(255,255,255,0.18) topographic overlay on the farm canvas and dark sections. Ambient texture that also communicates elevation and drainage — decoration that does a job.
Every chart displays its number. There is no chart without a visible numeric readout.
No 3D charts, no pie charts, no shadows on data, no legends where direct labelling is possible.
5.3 Visualising conformal uncertainty
This is FLIP's most important and most under-designed surface in v3.0. A bare "96.4%" is not trust; it is a number the farmer cannot interrogate.

┌────────────────────────────────────────────────────────────┐
│  CONFIDENCE                                                │
│  ▨▨▨▨▨▨▨▨▨▨▨▨▨▨▨▨▨▨▨▨▨▨▨▨▨▨▨▨▨▨░░░░  96.4%                 │
│  Prediction set: 1 of 12 possible causes                   │
│  ◉ Verified by model  ·  α = 0.05                          │
└────────────────────────────────────────────────────────────┘
Set size 1 → a single filled coverage bar in --leaf-700 with P1 stripes. Confident state.
Set size 2–3 → stacked candidate chips, each with its own coverage bar, ordered by score. The card header switches to the warning pictogram. Copy changes from "This is" to "This is most likely."
Set size > 3, or abstention → the coverage bar is replaced by a dashed amber container carrying the expert's avatar, name, and an ETA. Never show a percentage in this state; showing one implies a certainty the model has explicitly declined to claim.
The set-size readout is a genuine sequence, so it is numbered. Nothing else in the product uses numbered markers unless it is also a real sequence.

6. Imagery, Pictograms, and the 3D Twin
6.1 Photography direction
Real, naturally lit photography of Indian smallholder plots — 0.5 to 3 acre scale, mixed cropping, bunded fields, drip lines, hand tools. Not North American monoculture aerials, which is what every agri-tech stock library defaults to and which farmers do not recognise as their own land.
Grade: slightly desaturated, cool shadows, warm highlights, 2–4% grain. Golden hour or overcast. Never oversaturated.
People are shown mid-work, not smiling at camera.
Scrim under text on full-bleed imagery: linear-gradient(to right, rgba(11,30,18,0.85), transparent 60%).
Format: AVIF with WebP fallback, responsive srcset, LQIP placeholder. Tier A ships no image above 120KB.
6.2 Cut-out object photography
Crop, input, and equipment chips use transparent-PNG photographs of the real object at 40×40 — tomato, brinjal, cotton boll, copper oxychloride packet, drip emitter — not icons. This single choice separates FLIP from every dashboard template, and for a low-literacy user a photograph of the actual packet is more recognisable than any abstract glyph.

6.3 Pictograms — the deliberate exception
Photography cannot express actions. Actions use a strict pictogram set: 2px stroke, rounded caps, 24×24 grid, no fill except for critical states, maximum four strokes per glyph.

The set is closed. Every pictogram is user-tested for recognition in at least three states before it ships, and a pictogram that fails recognition testing is redrawn, not captioned around.

6.4 The 3D Farm Digital Twin
The centrepiece of the Farmer Dashboard, and the screen's one bold element.

Rendered as a photoreal isometric plot floating in soft fog — a miniature of the farmer's actual land, with real field boundaries from the PostGIS geometry, real crop textures, and real drip-line placement.
Field polygons carry the heatmap ramp and pattern overlay from §5.2.
Floating annotation pills anchor to fields: a --r-full glass pill, 1px rgba(255,255,255,0.25) border, connected to its anchor by a 1px line terminating in a 6px ring-with-dot marker. Example: Tomato Bed A · 88% humidity.
Tapping a field lifts it 8px and opens its detail sheet.
Never low-poly, never a blob, never a vector illustration. The credibility of the whole product rests on this canvas looking like the farmer's real land.
At flat device tier or with reduced motion: a pre-rendered static orthographic image with an SVG polygon overlay. Same information, same interactions, zero GPU cost.
6.5 What is banned
Zero flat vector illustration. Zero 3D blob shapes. Zero emoji in production UI. Zero abstract "AI" glow orbs.

7. Atomic Component Library
ATOMS
├── Button (Primary lime, Secondary forest, Ghost, Danger, Voice FAB)
├── StatPill (icon tile + label + metric + sparkline)
├── Input (OTP boxes, Voice trigger, Camera shutter)
├── Badge (Coverage %, Sensor health, CRDT sync, Expert verified)
├── Pictogram (closed set, 24×24, 2px stroke)
├── PatternSwatch (P1–P4 legend atom)
├── Avatar (Initials, role-coloured ring, verified tick)
└── EvidenceChip (tappable sensor reference inside WHY copy)

MOLECULES
├── AdvisoryCard (NOW / NEXT / WHY / CONFIDENCE)
├── SensorLiveCard (value, 24h sparkline, quality-flag bar)
├── ConfidenceBlock (coverage bar / candidate set / abstention)
├── VoiceCopilotFAB (audio visualiser, live transcript, TTS)
├── DisasterBanner (solid-surface emergency modal + siren control)
├── FieldAnnotation (anchored glass pill for the farm canvas)
├── SyncStrip (offline state, pending count, last-synced)
└── FarmMapWidget (MapLibre vector tiles + field boundaries)

ORGANISMS
├── FarmerDashboard (3D twin canvas + HUD + advisory carousel)
├── ExpertQueue (uncertainty-sorted cases + dual image viewer + diagnosis)
├── FPODashboard (cluster heatmap, bulk dispatch, input order table)
└── GovtDashboard (district hotspot map, containment polygon editor)
7.1 Buttons
Variant	Surface	Text	Geometry
Primary	--lime-400	--ink-900	--r-full, 72dp tall (Tier A) / 44px (Tier B), padding 0 32px
Secondary	--leaf-800	--ink-inv	same geometry
Ghost	transparent, 1.5px rgba(ink,0.16) border	--ink-900	same geometry
Danger	--alert-700	#FFFFFF	same geometry, requires hold-to-confirm
Voice FAB	--lime-400	—	72dp circle, --e3
Press state: translateY(1px) plus a 6% darken, 160ms --ease-micro. Tier A buttons carry a 40ms haptic tick on press. Label text names exactly what happens — "Mark completed," never "Submit" — and the same verb carries through to the confirmation toast.

7.2 StatPill — the signature component
┌──────────────────────────────────────────┐
│ ⬤  Soil moisture                         │
│    32%  ▁▂▃▅▄▃▂  ▨▨▨▨▨▨░░               │
└──────────────────────────────────────────┘
  ↑      ↑         ↑        ↑
  32px   label     24h      quality-flag bar
  icon   14px      spark-   (solid = measured,
  tile   --ink-600 line     dashed = interpolated)
--r-full container, 72dp tall on Tier A, --paper or --glass-light. Value in metric-m with tabular figures. These sit in a horizontal scroll row of 3–5, gap 12px. This is the at-a-glance layer, and it is the component most reused across all four organisms.

7.3 AdvisoryCard
┌────────────────────────────────────────────────────────────────────┐
│▩│ ⚠  Tomato early blight risk                        [96% ▨▨▨▨░] │
│▩├────────────────────────────────────────────────────────────────┤
│▩│ NOW                                                            │
│▩│ Spray copper oxychloride, 2.5 g per litre, before 5:00 PM.     │
│▩│                                                                │
│▩│ NEXT                                                           │
│▩│ Check the undersides of lower leaves again in 48 hours.        │
│▩│                                                                │
│▩│ WHY                                                            │
│▩│ Canopy humidity stayed above [88% for 9 hours] with [leaf      │
│▩│ wetness detected]. Temperature [21–25°C] matches the           │
│▩│ germination threshold for Alternaria solani.                   │
│▩├────────────────────────────────────────────────────────────────┤
│▩│ [ 🔊 Listen in Marathi ] [ 📷 Verify spray ] [ ✓ Mark done ]   │
└────────────────────────────────────────────────────────────────────┘
 ↑
 4px severity rail: colour + pattern, full card height
Anatomy:

Severity rail, 4px, left edge, carrying both the status colour and its pattern. Readable at a glance while scrolling, and readable in greyscale.
Header: 40px pictogram tile, title-l title, ConfidenceBlock chip right-aligned.
NOW is set in title-m — the largest type in the card. It is the only block a farmer must read.
NEXT in body, --ink-600.
WHY in body-l, with EvidenceChips inline — the bracketed values above are tappable, opening a popover with the causal mini-graph and the raw sensor series. This is where "transparent WHY" becomes real rather than rhetorical.
Footer: three 72dp actions. Listen is secondary, Verify is ghost, Mark done is primary lime. On Tier A they stack to full width if the language string exceeds the row.
Offline: a SyncStrip appears above the footer — "Saved on your phone · will sync when you're back online" — and Mark done commits locally and instantly with a pending badge.
7.4 VoiceCopilotFAB
72dp lime circle, bottom-right, inside the thumb zone, --e3.
Wake word detected → three concentric lime rings pulse outward from the FAB and the screen border picks up a 2px lime glow. (Changed from v3.0's gold glow: gold carried no meaning in the token system, and lime already means "the system is ready for your action." One accent, one meaning.)
Listening → the FAB expands into a --r-full bar carrying a live waveform visualiser driven by actual mic amplitude, not a canned animation.
Transcribing → live partial transcript above the bar in body-l, in the farmer's own script.
Speaking (TTS) → the waveform inverts to outbound, and the relevant field on the 3D canvas is highlighted in sync with the audio.
Every state carries a distinct haptic signature, so the interaction works with the phone at the ear.
7.5 DisasterBanner
The one component that ignores the aesthetic entirely.

Full-screen, solid --alert-700, #FFFFFF text at 7:1+. No glass, no blur, no transparency, at any device tier.
display-m headline, the immediate checklist in body-l, one 96dp primary action.
Slow 2s opacity pulse on the border, retained under reduced-motion because it is a safety signal.
Continuous haptic pattern plus Web Audio siren, with a clearly labelled silence control that stops audio but never dismisses the banner.
Renders from cache with zero network dependency.
8. Screen Architecture
8.1 Farmer Dashboard (Tier A)
┌─────────────────────────────────────────────┐
│ नमस्ते रमेश  ·  खेड, पुणे          🌧 18h  │  ← ambient: glass permitted
├─────────────────────────────────────────────┤
│ [Soil 32%▁▂▃] [Temp 24°C] [Humidity 88%▃▅] │  ← StatPill row, h-scroll
├─────────────────────────────────────────────┤
│                                             │
│        ╱▔▔▔▔▔▔▔▔▔▔▔▔╲                       │
│      ╱   3D FARM TWIN  ╲   ⬤ Tomato A      │  ← the one bold element
│     │  (isometric, fog) │     88% humidity  │
│      ╲   ▨▨ ⁘⁘ ▩▩     ╱                    │
│        ╲▁▁▁▁▁▁▁▁▁▁▁▁╱                       │
│                                             │
├─────────────────────────────────────────────┤
│ ┌───────────────────────────────┐ ┌───────  │  ← advisory carousel,
│ │▩│ ⚠ Early blight risk    96% │ │▨│ ✓ Ir  │     next card peeks 24px
│ │ │ NOW: Spray before 5 PM      │ │ │ NOW:  │
│ └───────────────────────────────┘ └───────  │
├─────────────────────────────────────────────┤
│ ⚡ 2 actions pending sync              [🎙] │  ← SyncStrip + Voice FAB
└─────────────────────────────────────────────┘
Layering: the twin canvas is the ground; the StatPill row and annotations float above at --e4; the advisory carousel is a solid-surface deck that the canvas scrolls behind. Decision-critical content never sits on glass.

8.2 Expert Studio (Tier B)
Dark tier, split 50/50. Left: the comparative dual-image viewer with a dotted circular scan reticle over the specimen and a 01 / 03 case-progress counter — a real sequence, so the numbering is earned. Right: a --glass-dark panel carrying the three-step diagnosis flow (Triage → Compare → Diagnose), each step expanding to reveal its evidence and controls.

Cases are sorted by epistemic uncertainty, not by timestamp. The queue's sort order is the product's core claim about expert time, so it is stated on screen rather than hidden in a settings menu.

8.3 FPO Dashboard (Tier B)
Regional cluster heatmap using the §5.2 ramp with pattern overlay, a bulk-dispatch panel, and an input order table. Dense, mouse-driven, 44px targets.

8.4 Government Dashboard (Tier B)
District hotspot map with a containment polygon editor. The polygon editor is the only place in FLIP where a destructive action is available without hold-to-confirm, because it is undoable — and it carries a visible undo stack for exactly that reason.

8.5 flip.farm public site (Tier B, full cinematic)
§	Section	Treatment
01	Hero	Full-bleed footage of a real smallholder plot at dawn. One line of copy bottom-left over scrim. No headline in the first frame — the footage carries it; the headline arrives on scroll.
02	Thesis	Dark chapter, display-l statement, supporting paragraph in the opposite column. Asymmetric.
03	Proof strip	Four metrics, 1px vertical rules between, counting up on entry.
04	The shift	The isometric farm render floating in fog, display-l overlaid.
05	Live demo	The real product: aerial plot with live annotations and the gradient legend. Pinned scroll sequence. This is the centrepiece.
06	How it works	Split 50/50 — film left with scan reticle, glass panel right with the three-step accordion.
07	Outcomes	Light chapter, white. Alternating copy/media rows, each media carrying one lime metric card in corner-bracket framing.
08	Evidence	Expert and FPO testimony, restrained, light.
09	Close	Deep chapter, diamond-masked image, display-xl statement, one action.
10	Footer	1px top rule, copyright left, credit right, 11px.
9. Key User Flows
Each flow now carries its UI choreography — the visual and motion response at each step — so that engineering and design read from one document.

Flow 1 — Farmer onboarding and instant farm binding
PostgreSQL
Core API
Keycloak IAM
Farmer PWA
PostgreSQL
Core API
Keycloak IAM
Farmer PWA
Farmer
Scans QR on welcome card / opens flip.farm
1
Workbox registers Service Worker (pre-caches shell)
2
Taps "Login with mobile number" (72dp, lime)
3
Request OTP (+91 XXXXXXXXXX)
4
6-digit SMS OTP via Twilio Verify
5
Enters OTP in 6 auto-advancing boxes
6
Validate OTP (PKCE exchange)
7
Access token + refresh token
8
POST /api/v1/auth/sync-profile
9
Upsert profile, fetch assigned farmer_farms
10
200 OK (profile, farms, active advisories)
11
3D twin assembles + village greeting in local language
12
Farmer
UI choreography

Shell paints in under 800ms on 3G — logo, language selector, and the login button, all from cache. No spinner at any point.
OTP boxes are 72dp squares, 12dp apart, --r-md, numeric keypad forced. A wrong digit shakes 6px once and clears only the last box, never the whole field.
The one orchestrated moment: the twin assembles field by field over 1200ms with --ease-out, each polygon rising from flat with its heatmap resolving last. This runs exactly once, at first login. Thereafter the canvas is simply present.
The greeting is spoken by Piper TTS simultaneously, so a non-reading user gets the same welcome.
Flow 2 — Daily voice advisory check
Farm Digital Twin
Whisper / Cloud Rasa
Local Porcupine WASM
PWA Client
Farm Digital Twin
Whisper / Cloud Rasa
Local Porcupine WASM
PWA Client
Farmer
Speaks "Hey Kisan" (wake word)
1
Wake detected — lime rings pulse, screen border glows
2
"Aaj tomato madhe paani dyayche ka?"
3
Audio buffer (or local Whisper.cpp)
4
Intent QUERY_IRRIGATION, field Tomato A
5
Soil VWC 32% (optimal), rain forecast in 18h
6
Piper TTS Marathi + highlights Tomato bed on twin
7
"No watering needed today. Rain expected tomorrow morning."
8
Farmer
UI choreography

Wake word: three concentric lime rings, 320ms, plus a 2px lime border glow and a single haptic pulse. Confirmation arrives before any network call, so the system feels instant even offline.
Listening: the FAB morphs to a full-width bar with a live amplitude waveform. The partial transcript types in above it in Devanagari as recognition firms up.
Answer: the Tomato A polygon on the twin lifts 8px and pulses its P1 stripe pattern in sync with the TTS audio, so the visual and spoken answers reinforce each other for a low-literacy user.
The spoken answer is also written in a StatPill — Watering: not needed · rain in 18h — which persists after the audio ends.
Flow 3 — Multimodal crop disease check
Expert Triage Queue
Conformal Engine
Cloud Triton Server
PWA Offline Cache
Mobile Camera
Expert Triage Queue
Conformal Engine
Cloud Triton Server
PWA Offline Cache
Mobile Camera
alt
[High certainty (set size = 1)]
[Ambiguous (set size > 1)]
alt
[Network available]
[Offline]
Farmer
Taps "Check crop health", snaps yellowing leaf
1
Captures 1080p image
2
Blur check, stores in IndexedDB
3
Image + 24h IoT readings + crop cycle ID
4
Softmax logits + feature embedding
5
Nonconformity scores (alpha = 0.05)
6
Early blight, 96.4%
7
Audio advisory + organic/chemical options
8
Routes to abstention review queue
9
"Sent to KVK agronomist (~30 min)"
10
"Photos sent to Dr. Priya Sharma."
11
Local Edge TFLite INT8 (MobileNetV3)
12
"Preliminary check: fungal risk. Will sync."
13
Farmer
UI choreography

Capture screen: 96dp shutter, a framing reticle sized to the leaf, and a live focus-quality ring that turns lime only when the frame is sharp enough to submit. This prevents the most common failure — a blurred photo — at the source rather than after upload.
Blur rejection is immediate and specific: "Too blurry to read. Hold steady and tap again." Never "Error."
Set size 1: the ConfidenceBlock renders a single striped coverage bar; the AdvisoryCard slides up with NOW visible above the fold.
Set size > 1: candidate chips stack, ordered by score, each with its own bar. Card copy shifts to "most likely." No single diagnosis is ever presented as settled.
Abstention: the ConfidenceBlock becomes a dashed amber container with Dr. Sharma's photograph, name, and a live countdown. The percentage is suppressed entirely. A named human face is the strongest available trust signal at the exact moment the model has declined to answer.
Offline: the card renders in a --soil-500 dashed-outline state (P4) with a sync badge. The preliminary result is shown as preliminary in both text and pattern — never styled to look like a confirmed diagnosis.
Flow 4 — Disaster early warning and siren trigger
Farmer
Farmer PWA
110dB Siren
Edge Gateway Pi
Alert Engine
IMD / NDMA Ingestion
Farmer
Farmer PWA
110dB Siren
Edge Gateway Pi
Alert Engine
IMD / NDMA Ingestion
par
[Edge siren broadcast]
[Cloud omnichannel push]
[Telecom fallback]
Severe flash flood + hail warning polygon
1
Intersects polygon with farms via PostGIS
2
MQTT emergency command (priority HIGHEST)
3
Hardware siren + looped emergency audio
4
WebSocket + WebPush emergency payload
5
Web Audio siren + continuous haptic
6
Full-screen modal with immediate checklist
7
Automated IVR call + WhatsApp template
8
UI choreography

The banner pre-empts everything, including an open camera or voice session, and restores that session state on dismissal.
Solid --alert-700, no glass, at every device tier. Headline in display-m. Checklist items are 96dp rows with pictograms, readable at arm's length.
One action: "I'm safe." Dismissal requires a deliberate 600ms hold, so it cannot be triggered by a panicked mis-tap.
The affected fields on the twin are outlined in the alert colour with P3 cross-hatch, persisting for 24 hours after dismissal.
Every channel carries the same sentence, verbatim, in the farmer's language — modal, siren audio, IVR, and WhatsApp. Divergent wording across channels during an emergency destroys trust faster than a missed alert.
Flow 5 — Expert review and ground-truth annotation
MLOps Pipeline
Core API
Expert Studio Web
MLOps Pipeline
Core API
Expert Studio Web
Agronomist
Opens /expert/queue (passkey authenticated)
1
Cases sorted by epistemic uncertainty
2
Selects case
3
Hi-res photo, 7-day soil moisture, heat index
4
Confirms "Bacterial spot (Xanthomonas)", sets dosage
5
POST /api/v1/advisories/{id}/expert-override
6
Dispatches notification to farmer Ramesh
7
Appends sample (label bacterial_spot, weight 2.0)
8
Agronomist
UI choreography

Queue rows carry an uncertainty bar rather than a timestamp. The most ambiguous case is visibly the most prominent, so the sort order needs no explanation.
Dual viewer: farmer photo left, reference specimen right, with a synchronised magnifier and a 1px measurement grid overlay.
The model's full prediction set is always visible with per-class coverage, so the expert corrects a visible claim rather than guessing at a black box.
Submitting animates the case card out of the queue and the farmer's avatar into a "notified" state — closing the loop visibly, which is what makes the queue feel like work that lands rather than work that disappears.
Keyboard-first: J/K to traverse, 1–9 to pick a class, Enter to commit. An expert clearing forty cases should never need the mouse.
10. Accessibility (WCAG 2.1 AA, AAA where it matters)
Requirement	Standard
Body text contrast	≥ 4.5:1 everywhere; ≥ 7:1 on Tier A (sunlight)
Critical alerts	≥ 7:1, solid surface, no transparency
Lime on ink-900	12.4:1 ✓ — white on lime is 1.5:1 ✗, banned
Status encoding	Colour + pictogram + pattern, always all three
Focus ring	2px --lime-400, 2px offset, visible on both light and dark surfaces
Touch target	72dp Tier A primary, 44px Tier B, 12dp minimum separation
Screen reader	aria-label, role, aria-live="polite" on sensor regions, aria-live="assertive" on emergencies
Reduced motion	All transforms → 200ms opacity; 3D canvas → static render, full function
Text on imagery	Always over a scrim, never directly on a photograph
Zoom	Layout holds to 200% without horizontal scroll
Sensor labels on glass	Solid scrim behind the text, never text on raw blur
The sunlight test: every Tier A screen is validated on a 400-nit display at 100,000 lux simulated illuminance. Anything that fails is redesigned, not brightened.

11. Multilingual Strategy
11.1 Coverage
Hindi (hi) · Marathi (mr) · Telugu (te) · Kannada (kn) · Gujarati (gu) · Punjabi (pa) · Bengali (bn) · Odia (or) · Assamese (as) · Indian English (en)

11.2 ICU MessageFormat
Pluralisation, Saka and Gregorian dates, and local area units (bigha, acre, guntha, katha) use standard ICU rules. Unit display follows the farmer's stated regional convention, not a national default — a Marathi farmer sees guntha, an Odia farmer sees katha, and the conversion is never shown unless requested.

11.3 Dynamic font loading
Only the active script's Noto Sans subset downloads. Inter Variable ships in the shell. Switching language triggers a subset fetch with a cached fallback, and the layout is designed to survive the swap without reflow — which is why every fixed-height card is spec'd against the tallest script, not the Latin one.

11.4 Dialect adaptation
TTS prompts use phonetic replacements for localised agricultural terms — tupka sinchan for drip irrigation in Marathi, tapak sinchai in Hindi. The written string and the spoken string are separate fields in the content model, because the word a farmer reads and the word they say are frequently not the same.

11.5 Layout consequences
Design every string container against Bengali and Telugu, which run 30–40% longer than English for the same content. If the layout survives those, it survives everything.
Buttons never use fixed widths. Tier A buttons stack to full width past a single line rather than truncating.
Numerals stay in Latin digits across all locales unless the user opts into Devanagari numerals — field-tested to reduce misreading of dosages, which is a safety issue, not a preference.
12. Performance Budget
Metric	Tier A target	Condition
First Contentful Paint	< 1.2s	3G, mid-tier Android
Largest Contentful Paint	< 2.5s	same
Initial JS	< 180KB gzipped	shell + critical path
Per-image ceiling	120KB	AVIF, responsive
Font payload	< 90KB	Inter Variable + one script subset
Interaction to Next Paint	< 200ms	all primary actions
Offline cold start	< 800ms	Service Worker cache
3D canvas, General Sans, and blur effects are all excluded from the critical path and load behind the shell.

13. Anti-Patterns — Instant Failure
Glass or transparency on any decision-critical or emergency surface
Lime used for status, decoration, or more than one element per region
White or light text on lime
Uniform radius regardless of nesting
Status communicated by colour alone
A chart without its number, or a solid-fill donut
Flat vector illustration, 3D blobs, emoji in production UI
ALL-CAPS labels, or micro type in any Indic script
Ambient, non-user-triggered motion on the Farmer PWA
A loading spinner that blocks cached content
01 / 02 / 03 markers on content that is not an actual sequence
A percentage displayed during model abstention
Two typefaces on Tier A, or General Sans shipped to the Farmer PWA
Stock aerials of North American monoculture standing in for Indian plots
14. Copy Voice
Write as a knowledgeable local advisor stating facts. Full sentences, concrete nouns, real numbers, sentence case. Active voice. A control names exactly what happens when it is used, and that verb survives into the confirmation.

Don't	Do
"Revolutionise your yield with AI"	"Spray copper oxychloride, 2.5 g per litre, before 5:00 PM."
"Error: sync failed"	"Not synced yet. Your 2 actions are saved on this phone."
"Submit"	"Mark completed" → toast: "Marked completed"
"No data available"	"No readings since Tuesday. Check the sensor in Tomato A."
"94.2% confidence" (on abstention)	"Sent to Dr. Priya Sharma for review. About 30 minutes."
Empty states are invitations, not apologies: "No advisories today. Your fields are in good shape." Failures explain what happened and what to do next, in the interface's voice — they never apologise and never stay vague.

Emergency copy is identical, word for word, across modal, siren script, IVR, and WhatsApp.

15. Implementation Handoff
Build order. Tokens → pictogram set → buttons → StatPill → ConfidenceBlock → AdvisoryCard → organism shells → page assembly. Ship the token file first and review it in isolation before any component exists.

Token delivery. One :root block of CSS custom properties, mirrored into tailwind.config.js via theme.extend. No component defines a raw hex value. A hardcoded colour in a component is a failed review.

Tier switching. <html data-tier="full|light|flat"> resolved once at boot (§3.6), with all glass, motion, and canvas rules scoped to that attribute. Never branch on user-agent strings.

Breakpoints. Tier A: 360 · 390 · 430. Tier B: 834 · 1280 · 1440.

Validation gates before merge. Sunlight contrast check · 72dp target audit · flat-tier render pass · reduced-motion pass · Bengali and Telugu string-length pass · axe-core clean · Lighthouse ≥ 90 on 3G throttle.

16. Changelog: v3.0 → v4.0
Area	Change	Rationale
Structure	Two-Tier Surface Doctrine added (§2)	The premium aesthetic and the field requirements are genuinely incompatible on one surface. Separating them lets both be fully served.
Colour	Added --lime-400 action accent; added humus-950, bone-50 grounds	v3.0 had no dedicated action colour — --leaf-700 carried both "healthy" and "tap here," which is a semantic collision.
Colour	Status colours now tier-paired	#C62828 on #121212 failed contrast in v3.0's dark mode.
Colour	Canvas changed #FAFAFA → #F4F3EC	A warm ground sits with soil and leaf tones; neutral grey fights them.
Type	Added metric-* scale and tabular figures	Data is the hero; v3.0 had no dedicated metric scale, so values were set in body sizes.
Type	Script-specific line-height and minimum sizes (§3.2)	Devanagari matras were being clipped at v3.0's 12px caption size. This was a live bug, not a refinement.
Type	Added General Sans for Tier B display only	Instrument personality without adding payload to the PWA.
Geometry	Flat 16px radius → nesting law (§3.4)	One radius on everything is the most visible amateur tell.
Motion	Added tiered motion + device throttle (§4)	v3.0 handled prefers-reduced-motion but not low-end GPUs, which is the more common constraint.
Glass	Capability gate added (§3.6)	Unconditional backdrop-filter would have shipped a slideshow to the target device.
Data viz	Pattern-first encoding (§5.1)	Delivers v3.0's colourblind-safe requirement without adding text, which matters for low literacy.
Data viz	Conformal uncertainty visualisation (§5.3)	v3.0 specified conformal prediction in the flows but never designed its display. A bare percentage is not transparency.
Imagery	Photography + cut-out objects; vector illustration banned (§6)	A photograph of the actual chemical packet is more legible to a low-literacy user than any glyph.
Twin	3D canvas spec'd as photoreal isometric with static fallback (§6.4)	Named as the screen's single bold element, and made cheap on weak hardware.
Components	AdvisoryCard rebuilt with severity rail + EvidenceChips (§7.3)	"Transparent WHY" needed an interaction, not just a paragraph.
Components	Wake-word glow changed gold → lime (§7.4)	Gold carried no meaning in the token system.
Components	DisasterBanner explicitly exempted from all aesthetics (§7.5)	Safety surfaces do not negotiate with visual identity.
Flows	All five flows annotated with UI choreography (§9)	v3.0 separated flow logic from visual response; engineering had to invent the latter.
New	Performance budget (§12), anti-patterns (§13), copy voice (§14), handoff gates (§15)	Absent from v3.0. Without budgets and gates, every rule above degrades on contact with a deadline.