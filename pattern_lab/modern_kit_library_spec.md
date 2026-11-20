<!-- Page 1 -->
Modern Kit Pattern Library
Modern Kit Pattern Library
For the Football Life 2027 dynamic kit mod. Version 1, 19 November 2026.
1. What this library is
This document specifies 144 modern pattern motifs in 18 families, plus a parameter system
that turns them into thousands of distinct kit designs. A motif is a rendering recipe for the
generator, not a finished image. Nothing here has been rendered yet: these are
specifications, and how good the kits look depends on the renderers you write and on the
validator in section 7.
There are three ways to address a design:
Motif only: M014 (144 motifs).
Curated recipe: M014-R07, one of 24 parameter sets applied to a motif . That gives 144
x 24 = 3,456 curated designs.
Open grammar: M014-S3D2O2-T1-Z1-C1-SL1, any legal combination of the axes in
section 3. That is 144 x 5 x 4 x 6 x 6 x 6 x 4 x 4 = 9,953,280 raw specs. The validator
keeps the good ones.
M-codes are a new namespace. The existing 001-205 catalog and its A-E modifiers are
untouched.
2. Hard rules
Banned as a body pattern, with no exceptions:
Equal-width vertical or horizontal stripes, hoops, and pinstripes at uniform spacing.
Two-colour halves, quarters, and any split with one straight boundary.
Plain checks and checkerboards.
A single sash, single chest band or single hem band as the only graphic.
A flat gradient as the only graphic.
Letters, numbers, words or real-world logos inside a pattern.
Required of every design:
At least two layers: base plus motif , or motif plus ghost or accent layer.
At least one non-uniform quality: scale, density, rotation or opacity must change
across the shirt.
Page 1 of 29

<!-- Page 2 -->
Modern Kit Pattern Library
Motif colours come only from the club palette and shades of it. The club primary stays
the dominant torso colour.
The chest sponsor rectangle is calmed: motif contrast there drops to 12 lightness
units or less, so a sponsor logo sits on the shirt with no plate or box behind it.
Clubs whose real identity is stripes or halves are handled in section 8.
3. Axes
Axis Code Meaning
Scale S1 Micro, motif about 14 px on the 480x500 design
canvas
S2 Small, about 28 px
S3 Medium, about 56 px
S4 Large, about 112 px
S5 Hero, one motif spans most of the torso, about 220
px
Density D1 / D2 / D3 / D4 Motif covers about 15% / 30% / 50% / 70% of the
zone
Orientation O1 Vertical flow
O2 Diagonal rising to the left
O3 Diagonal rising to the right
O4 Radial from an off-centre point
O5 Rising from the hem
O6 Draping from the shoulders
Treatment T1 T onal: motif is a shade of the body colour, 6-12
lightness units apart
T2 Duotone: second colour, up to 45 units apart
T3 Accent highlights: accent colour on only 10-18% of
motif area
Page 2 of 29

<!-- Page 3 -->
Modern Kit Pattern Library
Axis Code Meaning
T4 Fade-through: motif opacity ramps from full to zero
along the orientation
T5 Negative space: outline of the motif knocked out
of a darker body shade
T6 Ghost offset: a second copy offset 6-10 px at 40%
opacity
Zone Z1 Full body
Z2 T orso panel with calm chest
Z3 Hem-up, to 60% of shirt height
Z4 Shoulder-down, to 55% of shirt height
Z5 Side panels only, outer 28% on each side
Z6 Asymmetric sweep, concentrated on one side and
fading across
Colour C1 Body plus a shade of body
C2 Body plus second colour
C3 Body plus accent, minor
C4 Body plus second plus accent
Sleeve SL0 Plain sleeves
SL1 Motif echoed at 60% scale
SL2 Cuff trim in second or accent colour
SL3 Shoulder yoke carrying the motif at full scale
Shorts take a quiet echo of the motif (T1, S2). Socks take a single top band in the second
colour and nothing else.
4. Recipe matrix
Apply any recipe to any motif: M014-R07 means motif M014 with the parameters of R07.
Page 3 of 29

<!-- Page 4 -->
Modern Kit Pattern Library
Recipe S D O T Z C SL Character
R01 3 2 1 1 1 1 1 Quiet tonal all-over
R02 4 2 2 2 2 2 2 Contrast torso panel
R03 2 3 4 3 1 3 1 Dense accent texture
R04 5 1 5 4 3 2 0 Hero fade from the hem
R05 3 3 3 6 2 4 3 Ghosted layered torso
R06 1 4 1 1 1 1 1 Fabric-grade micro texture
R07 4 2 6 3 4 3 2 Large shoulder-down accent
R08 3 2 2 5 6 2 1 Outline negative space, side sweep
R09 5 2 4 4 1 4 3 Hero radial fade
R10 2 2 5 2 3 2 2 Small contrast rising from hem
R11 4 3 3 1 5 1 0 Large tonal side panels
R12 3 1 1 6 6 3 1 Sparse ghost sweep
R13 2 4 2 3 2 4 2 Dense small accent torso
R14 5 1 6 5 4 2 0 Hero negative-space drape
R15 3 3 4 2 1 2 1 Medium radial duotone
R16 4 1 5 1 3 1 3 Large tonal rise
R17 1 3 3 4 2 3 1 Micro fade torso
R18 4 4 2 6 1 4 2 Large dense ghosted all-over
R19 2 1 6 3 5 2 0 Sparse accent flanks
R20 5 3 1 2 6 4 3 Hero contrast asymmetric
R21 3 4 5 5 2 1 1 Negative-space rising torso
R22 4 2 4 3 4 3 2 Large radial accent drape
R23 1 2 2 1 3 2 0 Micro tonal hem-up
R24 5 2 3 6 1 4 3 Hero ghosted diagonal
R06 and R23 are texture-grade (S1). Use them only for home kits or as an under-layer
beneath another recipe, and exempt them from the periodicity test in section 7.
5. Motif library
Each line says what the renderer must draw. Every motif is seeded from club, season and
slot, so two clubs using the same code still get different shapes.
Page 4 of 29

<!-- Page 5 -->
Modern Kit Pattern Library
Family 1: Fractured Geometry
M001 Shard Field - triangulated low-poly shards that grow larger toward the hem
M002 Apex Fracture - a radial crack burst from the left shoulder with offset plates
M003 Prism F acets - large faceted planes with per-facet tonal shifts
M004 Shattered Glass - impact-point radial cracks with fine secondary fractures
M005 F ault Plates - tectonic slabs sliding past each other at irregular angles
M006 Crystal Lattice - interlocking crystal clusters of mixed size
M007 Drift T riangles - tessellated triangles whose size and opacity drift across the
torso
M008 Broken Hex - hex cells that fracture and detach toward one flank
Family 2: Topographic and Contour
M009 Contour Rings - closed elevation rings around two off-centre peaks
M010 Ridge Lines - wandering ridge curves of varying weight that merge and split
M011 Seismic T race - jagged seismograph traces layered at different amplitudes
M012 Tidal Contours - nested shoreline curves with sand-bar breaks
M013 Dune Ripple - wind-shaped ripple crests with irregular spacing
M014 Heat Map - thermal blobs with stepped edges
M015 Isobar Swirl - weather-chart pressure swirls with cell centres
M016 T errain Hatch - cross-hatched slope shading over a contour base
Family 3: Data and Signal
M017 Spectrum Burst - audio-spectrum columns of random height rising from the
hem
M018 Pixel Dissolve - square pixels thinning from dense to sparse across the shirt
M019 Glitch Shift - data slices displaced left and right with a colour split, never full-
width bars
M020 Moire Scan - two fine grids at a small angle producing interference ripples
M021 Code Rain - falling dotted trails of varying length and fade
M022 Circuit T races - right-angle trace routes ending in node pads
M023 Pulse Lines - heartbeat and waveform lines crossing the torso diagonally
M024 Radar Sweep - concentric range arcs with a faded sweep wedge
Page 5 of 29

<!-- Page 6 -->
Modern Kit Pattern Library
Family 4: Fluid and Organic
M025 Liquid Marble - swirled marbling in two or three tones
M026 Ink Bleed - dark ink blooms spreading through lighter fibre
M027 Smoke Plume - rising soft plumes with wispy edges
M028 Ocean Swell - layered swell curves with foam speckle
M029 Lava Flow - branching glowing channels over a cooled crust
M030 Aurora V eil - draped translucent curtains of light
M031 Silk Ripple - fabric-fold highlights radiating from a pinch point
M032 Cell Membrane - organic Voronoi cells with thick irregular walls
Family 5: Textile Jacquard
M033 Rib Jacquard - tonal knit-rib relief broken by diamond inserts
M034 Honeycomb Jacquard - tonal honeycomb with graded cell depth
M035 Quilt Diamond - padded-quilt diamond lattice with varied cell size
M036 Basket W eave - tonal woven blocks that change orientation by zone
M037 Chevron Mesh - layered chevron weave with fading rows
M038 Perforation Gradient - vent-hole dots shrinking from the hem to the chest
M039 Lattice Crest - generic shield-shaped cells in a lattice, no text
M040 Micro Hex - fine hex mesh with a soft vignette of density
Family 6: Speed and Motion
M041 Slipstream - tapered curved streaks sweeping around the torso
M042 V elocity Blur - ghosted repeats of one shape trailing from a leading edge
M043 Wind T unnel - flow lines bending around an invisible central obstacle
M044 Chevron Cascade - stacked arrow shapes that shrink and fade as they climb
M045 Jet T rails - long arcing vapour trails crossing at shallow angles
M046 Skid Arcs - rubber-mark arcs of changing weight
M047 T urbine Radial - curved blade shapes spinning out from a hub
M048 Motion Echo - a bold shape repeated at falling opacity along a path
Page 6 of 29

<!-- Page 7 -->
Modern Kit Pattern Library
Family 7: Architectural and Urban
M049 Skyline Rise - city silhouettes of irregular height rising from the hem into a
tonal haze
M050 Brutalist Blocks - chunky offset concrete-style slabs with shadow edges
M051 Cable Bridge - suspension-cable curves with tower verticals
M052 Roof T russ - stadium-roof triangulated truss geometry
M053 T errace Mosaic - stadium-seating cells with scattered gaps and bright dots
M054 Floodlight Beams - fanned beams from an upper corner with haze falloff
M055 Street Grid - an abstract city-map network with one highlighted route
M056 Tile Mosaic - geometric ceramic-tile mosaic with broken repeats
Family 8: Heritage Reinterpreted
M057 Deco F an - art-deco fans overlapping in tonal layers
M058 Interlace W eave - over-under knotwork bands that thin and thicken
M059 Star Lattice - an eight-point star lattice inspired by traditional geometric
tilework
M060 Key Fret Broken - a fret border motif fragmented across the torso
M061 Deconstructed Plaid - overlapping translucent bands at varied widths and
angles with fraying edges
M062 W ax-Print Bloom - abstract bloom and ring forms inspired by wax-print cloth
M063 W oven Strip Geometry - stepped interlocking blocks inspired by woven-strip
cloth
M064 Resist-Dye Cloud - indigo-style resist-dye clouds and rings inspired by adire
cloth
Family 9: Nature and Wildlife
M065 Rosette F ade - leopard-style rosettes shrinking toward the sleeves
M066 Feather Barbs - layered feather vanes in a tonal gradient
M067 Armour Scales - overlapping scale arcs with a highlight sweep
M068 Wing V eins - dragonfly-wing vein network with translucent cells
M069 Coral Branch - branching coral forms growing from the hem
M070 Leaf V enation - oversized leaf-vein networks in outline
M071 Ridge Mist - misty mountain ridges with irregular peaks in tonal steps
Page 7 of 29

<!-- Page 8 -->
Modern Kit Pattern Library
M072 Storm Front - roiling cloud mass with sharp lightning-fork highlights
Family 10: Cosmic and Light
M073 Nebula Dust - soft nebula clouds with star specks
M07 4 Constellation Net - node-and-link star maps of varied density
M075 Orbit Rings - offset eccentric ellipses with small satellite dots
M076 Eclipse Halo - an off-centre dark disc with a corona glow
M077 Starburst Offset - rays from a point beyond the shoulder, varying in length
M078 Bokeh Flare - soft lens-flare discs of varying size
M079 Gravity W arp - a grid bent around a heavy point mass
M080 Meteor Shower - diagonal streaks with glowing heads and scattered debris
Family 11: Mechanical and Tech
M081 Carbon F ade - carbon-weave texture that dissolves into plain colour
M082 Gear Ring - partial gear-tooth rings meshing at different scales
M083 Blueprint Callouts - fine technical linework with measurement ticks
M084 Rivet Plates - riveted armour plates with offset seams
M085 T urbo Spiral - a spiral of compressor blades around a chest-offset axis
M086 Piston Stack - chevron stacks resembling engine pistons
M087 V ent Mesh - angled vent cells forming a mesh with variable openings
M088 Cable Braid - braided cable strands twisting across the torso
Family 12: Abstract Brush and Art
M089 Dry Brush - dry-bristle brush swipes with broken edges
M090 Spray Splatter - aerosol splatter with a soft fall-off cloud
M091 Halftone Gradient - halftone dots fading from heavy to nothing
M092 Riso Overprint - offset overprinted shapes with deliberate misregistration
M093 P aper Collage - torn-paper layers with soft shadows
M094 Charcoal Smudge - smudged charcoal strokes in a tonal shade of the body
colour
M095 W atercolour Bloom - blooming wet-edge washes
M096 T ag Fragments - abstract graffiti line fragments, never legible text
Page 8 of 29

<!-- Page 9 -->
Modern Kit Pattern Library
Family 13: Optical and Illusion
M097 Op-Art Ripple - warped concentric ripples from an off-body point
M098 Moire Rings - two interfering ring sets producing beat patterns
M099 Isometric Cascade - isometric cubes tumbling down in shifting scale
M100 Ribbon Fold - a twisted ribbon with visible fold shading
M101 W arped Grid - a regular grid pinched and bulged by distortion
M102 Mirror Kaleidoscope - kaleidoscopic mirror segments around a chest-offset
centre
M103 Lenticular Shift - layered offsets simulating a lenticular colour flip
M104 Depth T unnel - receding polygonal frames pulling toward one flank
Family 14: Gradient Hybrids
M105 Hem Burst - a glow rising from the hem with film grain
M106 Mesh Blobs - three to five soft colour blobs blended as a mesh gradient
M107 Duotone Dissolve - body colour dissolving into a second colour through noise
M108 Spectral Bloom - a bloom of adjacent hues drawn only from the kit palette,
never a rainbow
M109 Diagonal Grain F ade - shoulder-to-hem diagonal fade with film grain
M110 Chest Glow - a radial glow offset from the logo area
M111 Corner Bleed - colour bleeding in from one lower corner
M112 Gloss Sweep - a soft specular highlight sweeping across a tonal base
Family 15: Heraldic and Symbolic
M113 Shield Repeat - small generic shield outlines at gradually changing size
M114 Laurel Line - laurel-leaf line art rising along the flanks
M115 Star Cluster - five-point stars clustered and fading
M116 Heritage Hatch - cross-hatched engraving texture in tonal ink
M117 Arrow Stack - layered arrow and chevron forms pointing upward
M118 Lozenge Chain - linked heraldic lozenges with varying fill
M119 Crown Linework - abstract crown-point silhouettes along the shoulder line
M120 Chain Link - interlocking chain links curving across the chest
Page 9 of 29

<!-- Page 10 -->
Modern Kit Pattern Library
Family 16: Football-Native
M121 Ball P anel F ade - football panel tessellation fading across the shirt
M122 Pitch Fragments - broken pitch-marking arcs and circles in outline
M123 Net W arp - goal-net mesh stretched as if struck
M124 Stud Matrix - boot-stud dots in a drifting matrix
M125 Movement Heat - a player heat-map blotch with contour edges
M126 P assing Network - node-and-link passing diagram across the torso
M127 Goal Arc Sweep - curved shot-trajectory arcs converging on a point
M128 T urf Cut - mown-turf diamond lattice with varied shading
Family 17: Panel and Collage
M129 Angular Blocking - four or more unequal angular colour panels, never a 50/50
split
M130 Plane Shift - offset layered planes with soft shadow edges
M131 Poly Overlap - overlapping translucent polygons
M132 Flank W edge - side-panel wedges flowing into the sleeve
M133 Y oke Geometry - a geometric shoulder yoke dissolving into the torso
M134 Slice Stack - irregular-width angled slices with varied tonal steps and fractured
ends
M135 Corner Arcs - large arcs anchored to opposing corners
M136 Interlock L - interlocking L -shaped forms of mixed scale
Family 18: Experimental Hero
M137 Pixel Camo - large-scale digital camouflage in kit tones
M138 Chrome Ripple - liquid-chrome ripple highlights
M139 Fibre Bloom - fibre-optic strands blooming from one point
M140 Neon Horizon - a perspective grid receding to a glowing horizon
M141 Holo Foil - a subtle iridescent foil shimmer drawn as tonal shifts
M142 Burnt Edge - scorched paper edges with ember glints
M143 Cracked Earth - dried-earth polygon cracks that widen toward the hem
M144 Ice Fracture - layered ice cracks with frosted fill
Page 10 of 29

<!-- Page 11 -->
Modern Kit Pattern Library
6. Slot rules and pool building
Slot Treatments
Scale Zones Club colour share
allowed
Home T1, T4 S1-S4 Z1, Z2,
Primary on at least 70% of the
Z3
torso
Away T2, T3, T4, T5 S2-S5 Z2-Z6 Lead colour on at least 60%
Third T2, T3, T6 S4-S5, plus D3-
any Lead colour on at least 40%
D4
Pool building for one club and slot:
1. T ake every motif and recipe pair (3,456) and drop pairs that break the slot rules above.
2. Drop pairs that fail the validator in section 7 on that club's real palette.
3. Shuffle the survivors with a seed made from the club id and slot. Season n takes entry
n, wrapping only after the pool is exhausted.
I expect each slot pool to stay well above a thousand designs, but count it on your real
palettes before relying on that figure. If a pool is smaller than you want, widen it with the
open grammar in section 1.
Family affinity
Use these as weights (about three times more likely), not as filters, so clubs still get
surprises.
Club trait Favoured families
Port or coastal city Industrial, steel, mining 4 (Fluid and Organic), 2 (Tidal Contours M012)
11 (Mechanical and T ech), 7 (Architectural and
Urban)
7, 13 (Optical and Illusion)
9 (Nature and Wildlife)
Capital or big city Animal nickname (Lions, Eagles,
Tigers)
T echnology sponsor or modern
stadium
3 (Data and Signal), 10 (Cosmic and Light)
Page 11 of 29

<!-- Page 12 -->
Modern Kit Pattern Library
Club trait Favoured families
Founded before 1920 5 (T extile Jacquard), 8 (Heritage Reinterpreted),
15 (Heraldic and Symbolic)
West African club 8, with extra weight on M062, M063 and M064
Speed nickname (Rapids, Jets, Flyers) 6 (Speed and Motion)
No trait available all families equal
7. V alidator
Run every candidate through these tests on a 96x96 render of the torso, before encoding
the texture. A failure sends the generator to the next pool entry, with up to 20 retries.
1. Separability (rejects stripes, hoops, checks, quarters). Fit lightness as a row term plus
a column term, using row means and column means. If that additive model explains
more than 80% of the variance, reject.
2. Split test (rejects halves). Cluster the render into two colours in Lab. If both clusters
cover at least 30% of the area and the boundary fits a straight line with mean error
under 2.5% of shirt height, reject.
3. Scale richness. Split the non-DC spectral energy into five octave bands from 8 px to
128 px. At least three bands must each carry 8% or more. This rejects single-scale
repeats.
4. Periodicity (rejects diagonal stripes and uniform tiling). Compute the 2D
autocorrelation. If one lag direction has a peak above 0.6 that repeats at least three
times, reject. Exempt: texture-grade designs (S1 with T1).
5. Contrast. Motif-to-body lightness gap: T1 and T4 and T6 at most 28 units, T2 and T3
and T5 at most 45 units, and at least 4 units for every design so it is visible. Inside the
chest sponsor rectangle the gap must be 12 units or less.
6. Identity colour . Share of torso pixels within 12 in CIE76 colour distance of the club
lead colour must meet the slot minimum in section 6.
7. Repetition. Compute a 64-bit perceptual hash of the torso. Hamming distance must
be at least 18 against the club's own kits from the last 8 seasons and its other two slots
this season, and at least 12 against other clubs in the same league this season.
Page 12 of 29

<!-- Page 13 -->
Modern Kit Pattern Library
Finish with a contact sheet of about 30 clubs x 3 slots x 3 seasons and look at it yourself .
The tests catch the failures I have listed; they cannot tell you whether a design looks
good.
8. Clubs whose real identity is stripes, hoops or halves
The identity data for some clubs will say their real kit is stripes or halves. This library still
never draws plain equal bars. For those clubs the generator renders an evolved structure:
Bar widths follow a ratio progression (each bar 0.62 of the one before it) instead of
equal widths.
contrast.
Bars carry tonal shifts (T1 or T4) and fade out before reaching both flanks at full
One motif from the club's affinity families is overlaid at two scales, so the design is not
made of bars alone.
The result must still pass tests 1 to 4. If it cannot, the generator drops the signature
structure for that season and uses a normal pool design in the club's real colours. It
never falls back to plain bars.
9. Anti-repetition rules
No recipe repeats for the same club within 6 seasons.
The same family never appears twice in a row for one club and slot.
At most 2 of a club's 3 slots may come from the same family in a season.
Within a league and season, a motif may be used by at most 2 clubs.
Seed every motif from club, season and slot, so shapes differ even when the code
matches.
Jitter parameters inside legal ranges (angle plus or minus 8 degrees, scale plus or
minus 12%, phase random) so no two renders of one code are identical.
Do not apply the same random seed to home, away and third.
10. Integration notes for the mod
Add the library as a new module and leave the old catalog alone.
1. Create kit
_patterns
_
modern.py next to kit
_patterns.py, holding the 18 families,
the 144 motif renderers, the recipe table from section 4, and a spec parser.
Page 13 of 29

<!-- Page 14 -->
Modern Kit Pattern Library
2. Spec grammar: M###, M###-R##, or M###-S#D#O#-T#-Z#-C#-SL#. Parse with this
pattern: ^M(\d{3})(?:-R(\d{2})|-S([1-5])D([1-4])O([1-6])-T([1-6])-Z([1-6])-
C([1-4])-SL([0-3]))$.
3. Give the pattern class a scale factor so pixel sizes in the motifs multiply by it, and
render at 2x supersampling before downsampling. The current engine draws at
480x500 and upscales, which softens edges.
4. In design
from
_
_
club, replace the fallback to the eight basic patterns with pool
selection from section 6. Keep kit
_patterns.draw for the numeric 001-205 codes.
5. After drawing the pattern, blend it toward the body colour inside the sponsor
rectangle with a feathered mask. Turn the sponsor plate off .
6. Put the tests from section 7 in a new kit
_
validate.py and call it before the texture
is encoded.
7. Build the contact-sheet script from section 7 so every change to a renderer can be
checked visually.
11. Machine-readable index
Axis order for recipes: S, D, O, T , Z, C, SL.
F01 Fractured Geometry M001-M008
F02 Topographic and Contour M009-M016
F03 Data and Signal M017-M024
F04 Fluid and Organic M025-M032
F05 Textile Jacquard M033-M040
F06 Speed and Motion M041-M048
F07 Architectural and Urban M049-M056
F08 Heritage Reinterpreted M057-M064
F09 Nature and Wildlife M065-M072
F10 Cosmic and Light M073-M080
F11 Mechanical and Tech M081-M088
F12 Abstract Brush and Art M089-M096
F13 Optical and Illusion M097-M104
F14 Gradient Hybrids M105-M112
F15 Heraldic and Symbolic M113-M120
F16 Football-Native M121-M128
F17 Panel and Collage M129-M136
F18 Experimental Hero M137-M144
R01 3,2,1,1,1,1,1
Page 14 of 29

<!-- Page 15 -->
Modern Kit Pattern Library
R02 4,2,2,2,2,2,2
R03 2,3,4,3,1,3,1
R04 5,1,5,4,3,2,0
R05 3,3,3,6,2,4,3
R06 1,4,1,1,1,1,1
R07 4,2,6,3,4,3,2
R08 3,2,2,5,6,2,1
R09 5,2,4,4,1,4,3
R10 2,2,5,2,3,2,2
R11 4,3,3,1,5,1,0
R12 3,1,1,6,6,3,1
R13 2,4,2,3,2,4,2
R14 5,1,6,5,4,2,0
R15 3,3,4,2,1,2,1
R16 4,1,5,1,3,1,3
R17 1,3,3,4,2,3,1
R18 4,4,2,6,1,4,2
R19 2,1,6,3,5,2,0
R20 5,3,1,2,6,4,3
R21 3,4,5,5,2,1,1
R22 4,2,4,3,4,3,2
R23 1,2,2,1,3,2,0
R24 5,2,3,6,1,4,3
Part 2: Retro, Engraved and Signature
Designs
12. What changed in this update
This update adds 144 motifs (M145-M288), an engrave layer for barely visible detail, retro-
era designs, and six signature studies based on the 2026/27 home kits you named:
Chelsea, Liverpool, Manchester City, PSG, Barcelona and Como. Facts about those kits
come from the clubs' and manufacturers' own release pages and kit-news coverage, read
on 19 November 2026.
Amendment to sections 2 and 8 (this overrides them wherever they conflict):
Filler patterns are unchanged. The ban on plain stripes, hoops, halves, quarters and
checks still applies to everything the generator picks from the pools.
Page 15 of 29

<!-- Page 16 -->
Modern Kit Pattern Library
Signature layouts are the exception. When a club's real kit is built on a structure (the
PSG central band, the Barcelona vertical bands, Como's tonal pinstripes), the mod
may draw that structure, because you asked for those kits to be matched.
Every signature layout must still carry at least one engraved or tonal overlay, use the
club's real colours, and use unequal widths wherever the real kit does.
A signature layout is used only for the club it models. No other club ever receives it as
filler.
No crest, logo, sponsor mark or text is part of any pattern. The mod places those
separately.
13. Signature studies
Each study lists what the real kit does, then the build in this library's codes. Building
blocks are defined in section 15.
SIG-CHE26H: Chelsea 2026/27 home
Real kit (Chelsea FC and Nike): Bright Blue base, the club crest woven into the front of the
fabric as a two-tone blue pattern, a collar with a button-down neck, Midwest Gold on the
badge and swoosh, and white socks with a laurel wreath that also rings the crest.
Y ou described gold lines down the sides of the torso running to the back. I did not find
that in the sources I read, so I have built it as your specification, not as confirmed detail.
Build:
Base: Bright Blue, exact.
M193 Interwoven Crest Field at engrave level EL2, zone Z2, front only.
M194 Laurel Ring Halo at EL2 around the crest position.
M282 Button-Down Collar Placket with a gold edge.
M268 Side Line Front-to-Back in gold, one narrow line on each side, continuing onto
the back (your spec).
Socks: white with a laurel band ( M194 at S2).
Other slots (sourced): the away kit is solid black with gold shoulder ribs ( M286) and a
laurel border on the collar and cuffs ( M284).
Page 16 of 29

<!-- Page 17 -->
Modern Kit Pattern Library
SIG-LIV26H: Liverpool 2026/27 home
Real kit (Liverpool FC and adidas): a re-imagined version of the 1989-91 geometric print of
jagged triangles. The red is deeper than usual, which adidas calls active maroon. The print
is louder than the original. White is used on the crest, the brand and the trims, and the
shorts and socks are deep red. The player version leaves clear space around the crest and
adidas logo.
I read your white line with a special design around the kit as the white trims plus the
geometric print.
Build:
Base: active maroon, exact, deeper than the classic red.
M154 Candy Triangles at S4 D3 O5 T2 Z1 C2, triangle tips fading to white.
Keep-out: contrast 12 units or less around the crest, brand and sponsor rectangles.
Collar and cuffs: M281 Polo Collar Tri-Trim in white.
Shorts and socks: plain deep red.
Optional overlay: M201 Micro Rib Emboss at EL1.
SIG-MCI26H: Manchester City 2026/27 home
Real kit (Manchester City and Puma): a full sky-blue gradient, darker at the shoulders and
lightening toward the hem, with a subtle geometric texture across the front and back
panels, a metallic monochrome crest, and white collar and cuffs. Sources disagree slightly
on shorts and socks: the latest coverage says white, an earlier preview said light blue.
Build:
M257 Shoulder-Dark Hem-Light Fade across the full body.
M211 Triangle Etch at EL1, zone Z1, continuing onto the back.
White collar and cuffs ( M285).
White shorts and socks.
SIG-PSG26H: PSG 2026/27 home
Real kit (PSG, Nike, ESPN and Goal): a brighter royal blue (their Old Royal) last used at
home 25 years ago, with an ultra-wide red-and-white central band that now continues
onto the back. The crest and swoosh are stacked in the middle of the chest and the
sponsor is shrunk to fit inside the band.
Page 17 of 29

<!-- Page 18 -->
Modern Kit Pattern Library
Build:
Base: royal blue, exact.
M265 Wide Central Band, front to back, red with a white inner band.
Logo and sponsor positions sit inside the band, so the chest keep-out follows the
band.
Overlay is optional ( M201 default.
at EL1). Y ou asked for the basic design, so leave it off by
Other slot (sourced): the away kit is mostly white with the central band drawn as fine
vertical lines fading from red to navy, an Op Art look. Build it as M265 plus M264
Gradient Band Fade.
SIG-FCB26H: Barcelona 2026/27 home
Real kit (FC Barcelona and Nike): vertical blaugrana bands in three reds (Deep Garnet,
Noble Red, Cardinal Red) and three blues (Game Royal, Loyal Blue, Blue Void), with the
shades inspired by the renovated Camp Nou facade. Blackened Blue is used on the collar
and cuffs, shorts and socks, with Mineral Y ellow branding. A semi-hexagonal collar is
reported.
Build:
M273 Graded Vertical Bands, three shades of each colour.
M274 Facade Panel Bands for the irregular widths.
M283 Semi-Hexagonal Collar and M285 Cuff Trio Trim, both Blackened Blue.
Shorts and socks: Blackened Blue.
Overlay: M235 Stadium Facade Panels at EL1.
SIG-COM26H: Como 1907 2026/27 home
Real kit (Como 1907 and adidas): a royal blue base with tonal pinstripes and a classic polo
collar. The cuffs carry white, red and gold trim and the branding is white. The kit was
designed with Como's Chief Brand Officer, Rhuigi Villaseñor. Press coverage ties the look
to the waters of Lake Como or the city flag; I could not confirm which, so I have not used
either as a motif .
Build:
Base: royal blue, exact.
Page 18 of 29

<!-- Page 19 -->
Modern Kit Pattern Library
M277 T onal Hairline Field at T1, no more than 5 lightness units, spacing drifting by 15%
with a few deliberate breaks.
M281 Polo Collar Tri-Trim and M285 cuffs in white, red and gold.
Overlay: M207 Jacquard Ripple at EL2.
14. New axes, recipes and retro rules
Engrave level
Engraved designs are low-contrast detail woven or embossed into the fabric, meant to be
hard to see.
Level Lightness gap from the body Reads as
EL1 3 to 4 units Found only on close inspection
EL2 4 to 6 units Barely visible
EL3 7 to 10 units Subtle
EL4 11 to 14 units Visible tonal pattern
BC3 texture compression can flatten very small differences. Do not go below 3 units, and
test every engraved layer after the encode step (section 17). If the game's kit materials
have a normal or specular map, putting the engraving there would survive better than in
the colour map. I have not checked whether the Football Life 2027 kit materials use those
maps.
Engrave recipes
These apply to any engraved motif (M193-M256), alone on the plain body colour or as an
overlay on another design. B1 means the engraving continues onto the back and B0 means
front only.
Recipe EL S D O Z B
E01 1 3 3 4 2 1
E02 2 2 4 1 1 1
E03 1 4 2 2 2 0
Page 19 of 29

<!-- Page 20 -->
Modern Kit Pattern Library
Recipe EL S D O Z B
E04 2 3 3 5 3 1
E05 3 2 3 3 1 1
E06 1 5 1 4 2 0
E07 2 1 4 6 4 1
E08 3 4 2 2 6 0
E09 1 2 4 1 5 1
E10 2 5 2 4 1 1
E11 3 3 2 5 3 0
E12 1 4 3 3 4 1
E13 2 3 1 6 2 0
E14 4 4 2 2 1 1
E15 1 2 3 5 6 1
E16 3 5 2 4 2 0
E17 2 1 3 1 1 1
E18 4 3 3 3 3 1
E19 1 3 2 6 5 0
E20 2 4 4 2 2 1
E21 3 2 2 4 4 1
E22 1 5 3 5 1 0
E23 2 3 4 3 6 1
E24 3 4 1 1 3 1
Retro rules
Retro motifs (M145-M192) are the loud abstract graphics of earlier eras. They break the
filler ban only in the sense that they are bold; they still contain no plain stripes, halves or
checks.
Contrast may go up to 55 lightness units, and S4-S5 with D3-D4 is allowed.
Use them mainly for away and third kits.
Heritage rotation: in any season where the season number divides by 5, a club's third
kit comes from the retro pool.
Page 20 of 29

<!-- Page 21 -->
Modern Kit Pattern Library
15. New motifs M145-M288
M145-M192 are retro. M193-M256 are engraved: use them as overlays or alone on a plain
body colour. M257-M288 are building blocks for signature studies, collars and trims, and
are not used as filler.
Family 19: Seventies Geometry (retro)
M145 Sunburst W edges - wide wedges radiating from the collar in alternating tones,
uneven widths
M146 Arch Roundels - concentric arches rising from the hem, thick to thin
M147 Y oke Chevron Flash - a deep V yoke across the chest with a layered double
edge
M148 Pennant Flags - overlapping pennant triangles pointing toward one shoulder
M149 Diamond Inset - a large chest diamond with stepped inner diamonds
M150 Zig Flash - a zigzag flash crossing the torso diagonally, broken in three
segments
M151 Roundel Spread - large overlapping circles in two tones, cropped by the side
seams
M152 Bolt Splice - lightning-bolt panel splices of unequal length
Family 20: Eighties Abstract (retro)
M153 T errazzo Chips - scattered irregular chips of three sizes in kit tones
M154 Candy T riangles - jagged faded triangles whose tips turn solid, late-eighties
graphic style
M155 Squiggle Confetti - squiggles, dots and short zigzags scattered at random
angles
M156 Brush Splash - wide brush splashes with drips toward the hem
M157 Pixel W ave - stepped pixel waves rising from the hem
M158 Halftone Burst - a halftone-dot explosion from the chest outward
M159 Shadow Lattice - a diamond lattice with an offset hard shadow on every cell
M160 Racetrack Loops - looping track-shaped curves intersecting across the torso
Family 21: Early Nineties Graphic (retro)
M161 Bruised Cloud - hard-edged overlapping blotches in two or three tones
Page 21 of 29

<!-- Page 22 -->
Modern Kit Pattern Library
M162 Shadow Blocks - large offset blocks with a stepped shadow
M163 T orn Zigzag - a torn-paper zigzag edge across the chest with a ghost copy
below
M164 Hexagon Overlap - large overlapping hexagon outlines in graded tones
M165 Scribble Lattice - hand-drawn crossing lines forming an irregular net
M166 Fractal T riangles - triangles subdivided into smaller triangles toward one corner
M167 Diagonal W ash - a grainy diagonal wash cut by two angled planes
M168 Cracked Mosaic - irregular mosaic tiles with thin bright joints
Family 22: Late Nineties Tech (retro)
M169 Sports Mesh P anels - hexagonal sports-mesh panels with piped seams in two
tones
M170 Seam P anels - bonded panel shapes divided by thin metallic-tone seams
M171 Flame Lick - flame-edged shapes rising from the hem with trailing licks
M172 Wireframe Globe - a latitude-and-longitude wireframe sphere partly cropped
by the chest
M173 Speed Slash - three angled slashes of unequal length and non-parallel angles,
with a ghost trail
M17 4 Carbon Dots - carbon micro dots in a staggered weave, thickest at the sides
M175 Circuit Bloom - sublimated circuit traces blooming from a central pad
M176 Spiral Burst - a spiral burst of tapered petals
Family 23: Two-Thousands Tonal (retro)
M177 T onal Swirl - soft tone-on-tone swirls drifting across the shirt
M178 P anel Piping - bonded shoulder panels outlined with piped contrast seams
M179 Ripple W eave - woven ripple texture radiating from the lower hem
M180 Cell F ade - rounded cells that shrink and fade across the torso
M181 Burst W eave - woven starburst clusters in a staggered layout
M182 Hex Emboss - large embossed hexes with a raised-edge highlight
M183 Shield Dissolve - generic shield outlines dissolving into dots
M184 Contour Net - fine netting that follows the torso contour
Page 22 of 29

<!-- Page 23 -->
Modern Kit Pattern Library
Family 24: Twenty-Tens Digital (retro)
M185 Pixel Cascade - pixel blocks cascading from one shoulder and shrinking as they
fall
M186 Mesh Diagonal - a diagonal mesh gradient between two kit tones with grain
M187 F aceted Gem - faceted gem shapes in three tones across the chest
M188 Neon Shard - angular shards edged with a thin bright keyline
M189 Layered Chevron Flow - chevrons layered at changing sizes with a flowing
offset
M190 Digital Smudge - smudged pixel-sort streaks fading toward the sleeves
M191 Mirror F acets - mirrored triangular facets reflecting across the centre line
M192 P aper Fold - origami-style folds with soft crease shading
Family 25: W oven Crest and Heritage (engraved)
M193 Interwoven Crest Field - a generic crest shape woven in two close tones across
the front panel
M194 Laurel Ring Halo - a laurel wreath ring around the crest position
M195 Beast Rampant Lattice - repeated generic rampant-beast outlines, no text or
real emblems
M196 Shield Chain W eave - shield outlines linked by thin chain lines
M197 Knot Repeat - an interlaced knot repeated at two scales
M198 Banner Fold - folded ribbon outlines drifting across the chest
M199 Coin Relief - circular medallion reliefs of mixed size
M200 Hatch Plate - engraving-hatch plates under the crest position
Family 26: Engraved Textile (engraved)
M201 Micro Rib Emboss - fine rib relief broken by diamond inserts
M202 Dobby Squares - woven dobby squares with offset steps
M203 Honeycomb Deboss - debossed honeycomb with graded depth
M204 Basket Relief - raised basket-weave relief that changes direction by zone
M205 V ent Dimples - vent holes shown as faint dimples
M206 T will P atches - twill-weave patches that shift direction by zone
M207 Jacquard Ripple - jacquard ripples spreading from the lower left
M208 Cable Knit - faint cable-knit twists in a staggered layout
Page 23 of 29

<!-- Page 24 -->
Modern Kit Pattern Library
Family 27: Engraved Geometry (engraved)
M209 F acet Deboss - large faceted shards debossed into the fabric
M210 Isometric Relief - faint isometric cube relief
M211 T riangle Etch - etched triangles in a graded field
M212 Hex Lattice Etch - an etched hex lattice with missing cells
M213 Radial Etch - radial etching from a chest-offset centre
M214 T essellation Ghost - a ghosted tessellation of mixed polygons
M215 W ave Etch - layered etched waves at irregular spacing
M216 Slice Contour - contour lines like a sliced topographic model
Family 28: Engraved Nature (engraved)
M217 Frost Etch - frost-crystal branching etched faintly
M218 V ein Emboss - leaf-vein networks embossed
M219 Ripple Deboss - circular water ripples debossed
M220 Shell Spiral - shell spirals etched at several sizes
M221 Pore Emboss - coral-pore texture embossed
M222 Grain Etch - bark-grain lines etched in drifting patches
M223 Cloud Relief - faint cloud forms in relief
M224 Plume Emboss - feather plumes embossed
Family 29: Engraved Light and Shadow (engraved)
M225 Shadow Planes - barely-there overlapping shadow planes
M226 Sheen Sweep - a faint diagonal sheen across a satin-like finish
M227 Hem Vignette - a subtle darkening at the hem and shoulders
M228 Lens Halo - faint concentric halos
M229 Caustic Net - an underwater caustic light network
M230 Prism Planes - a prism split drawn as tonal planes, never a rainbow
M231 Fold Shadow - soft fabric-fold shadows
M232 Dusk Grain - a grain-textured gradient
Family 30: Engraved Urban and Sport (engraved)
M233 Pitch Grain - mown-pitch pattern as a faint relief
Page 24 of 29

<!-- Page 25 -->
Modern Kit Pattern Library
M234 Net Relief - goal-net knots as a faint relief
M235 Stadium F acade P anels - panel joints of a stadium facade at varied widths
M236 T errace Step Etch - stepped terrace geometry etched
M237 Skyline Etch - a skyline contour etched at the hem
M238 Street Map Etch - street-map lines etched across the front
M239 T rack Bend Etch - curved athletics-track lane lines in a bend
M240 Stud Deboss - boot-stud dots debossed in clusters
Family 31: Engraved Symbols (engraved)
M241 Star Field Etch - scattered stars etched at several sizes
M242 Crown Point Etch - abstract crown points etched along the shoulder line
M243 Arrow Chevron Emboss - layered arrow chevrons embossed pointing upward
M244 Lozenge W eave - interwoven lozenges of varying size
M245 Chain Link Deboss - interlocking chain links debossed
M246 Fleck T errazzo - faint terrazzo flecks
M247 Compass Rose Etch - compass-rose geometry etched
M248 Sunray F an Etch - fanned rays etched from a corner
Family 32: Engraved Tonal Systems (engraved)
M249 Gradient W eave F ade - a woven texture whose scale grows with a gradient
M250 Dot Matrix Ghost - a ghosted dot matrix drifting across the torso
M251 Grid Relief W arp - a relief grid warped by a soft bulge
M252 Cell Relief Drift - soft cells drifting and merging
M253 T onal W ave Relief - broad tonal waves in relief
M254 Soft Mosaic Etch - a soft mosaic etched with irregular tiles
M255 Pebble Relief - river-pebble relief
M256 Spore Dust Relief - fine spore-like dust in relief
Family 33: Gradient Structures (building blocks)
M257 Shoulder-Dark Hem-Light F ade - a full gradient, darker at the shoulders and
lightening toward the hem
M258 Radial Dual- T one F ade - a two-tone fade radiating from the chest
Page 25 of 29

<!-- Page 26 -->
Modern Kit Pattern Library
M259 Hem W ash - a wash toward white or a light tint at the hem
M260 Stepped Grain Gradient - a gradient built from soft steps with film grain
M261 Diagonal T onal F ade - a diagonal fade between two shades of the base colour
M262 Centre Glow F ade - a lighter glow in the middle fading to darker edges
M263 Side Vignette - darker sides fading toward the centre
M264 Gradient Band F ade - a band whose colour fades from one kit colour to another
Family 34: Central and Panel Structures (building blocks)
M265 Wide Central Band - an ultra-wide centre band from collar to hem, front to
back, with an inner band in a second colour
M266 Offset Central Band - a wide band shifted to one side
M267 Stepped Central P anel - a centre panel whose edges step in at the chest and
hem
M268 Side Line Front-to-Back - a narrow line on each side running from the front
across the side seam to the back
M269 Single Side Line - one asymmetric line along one flank
M270 Sleeve- Through Flash - a flash running from the torso through one sleeve
M271 Wide Y oke P anel - a wide shoulder yoke in a second tone
M272 Side Seam T rim - a trim along the side seam only
Family 35: Banded Identity Layouts (signature use only)
M273 Graded V ertical Bands - vertical bands in three shades of each club colour with
irregular widths
M27 4 F acade P anel Bands - band edges cut like stadium facade panels
M275 E volved Hoops - hoops with a 0.62 width progression and tonal breaks
M276 E volved Halves - halves with a fractured, offset seam and a tonal overlay
M277 T onal Hairline Field - tonal hairlines of 5 units or less, with drifting spacing and
gaps
M278 T onal Wide Bands - wide bands only a few units apart in tone
M279 E volved Sash - a sash with a broken edge and a tonal echo
M280 E volved Quarters - quarters with offset corners and a tonal overlay
Page 26 of 29

<!-- Page 27 -->
Modern Kit Pattern Library
Family 36: Trim and Collar Systems (building blocks)
M281 Polo Collar T ri- T rim - a polo collar with three trim colours
M282 Button-Down Collar Placket - a collar with a button-down placket edge
M283 Semi-Hexagonal Collar - a collar with a six-sided cut
M284 Laurel Border Collar - a collar and cuff border with a laurel motif
M285 Cuff T rio T rim - a three-colour cuff trim
M286 Engineered Shoulder Ribs - raised rib panels on the shoulders
M287 Hem T ape T rim - a tape trim along the hem
M288 Back-Collar P anel - a small panel under the back collar, with no text
16. Counts and new code forms
Code forms added by this update:
M###-E##: an engraved motif (M193-M256) alone on the plain body colour, with an
engrave recipe.
M###-R##+G###-E## : any base design plus an engraved overlay motif and engrave
recipe. Example: M014-R07+G211-E05.
SIG-XXX26H: a signature study from section 13.
Counts:
Motifs: 144 from part 1 plus 144 new, 288 in total. M257-M288 are building blocks, so
256 motifs are filler-eligible.
New curated designs: 112 new filler motifs (M145-M256) x 24 recipes = 2,688, plus 64
engraved motifs x 24 engrave recipes = 1,536. That is 4,224 new curated designs.
All curated filler designs: 3,456 from part 1 plus 4,224 = 7,680.
Overlay combinations: 6,144 filler base designs x 64 overlay motifs x 24 engrave
recipes = 9,437,184.
Raw grammar across all 288 motifs: 288 x 69,120 = 19,906,560.
None of the new motifs repeats a form from part 1. Where a new motif is close to an old
one (for example M039 and M193), the new one is an engraved overlay at EL1-EL4 and the
old one is a visible jacquard pattern.
Page 27 of 29

<!-- Page 28 -->
Modern Kit Pattern Library
17. V alidator additions
Add these to the tests in section 7.
8. Engrave visibility . Measure the overlay's local high-pass contrast. It must fall inside
the lightness range for its engrave level. Overlays are exempt from tests 1-4 and from
the minimum-contrast rule in test 5, but the base design underneath must still pass all
of them.
9. Compression survival. Encode the texture to BC3, decode it, and measure the
overlay again. If its contrast falls below 60% of the original, raise the level by one
(maximum EL4) and re-test. If it still fails, drop the overlay.
10. Signature check. A signature layout is exempt from tests 1 and 2 for its identity
structure only. With the overlay counted, it must pass tests 3-7, and its band and bar
colours must be within 12 in CIE76 colour distance of the colours sampled from the
real kit texture.
11. Retro check. Retro motifs may reach 55 lightness units of contrast, appear only in
away and third slots, and follow the heritage rotation in section 14.
12. Overlay repetition. A club may not reuse the same overlay motif within 8 seasons, and
the overlay's family must differ from the base motif's family.
18. Machine-readable additions
Axis order for engrave recipes: EL, S, D, O, Z, B.
F19 Seventies Geometry M145-M152 retro
F20 Eighties Abstract M153-M160 retro
F21 Early Nineties Graphic M161-M168 retro
F22 Late Nineties Tech M169-M176 retro
F23 Two-Thousands Tonal M177-M184 retro
F24 Twenty-Tens Digital M185-M192 retro
F25 Woven Crest and Heritage M193-M200 engraved
F26 Engraved Textile M201-M208 engraved
F27 Engraved Geometry M209-M216 engraved
F28 Engraved Nature M217-M224 engraved
F29 Engraved Light and Shadow M225-M232 engraved
F30 Engraved Urban and Sport M233-M240 engraved
F31 Engraved Symbols M241-M248 engraved
F32 Engraved Tonal Systems M249-M256 engraved
F33 Gradient Structures M257-M264 block
F34 Central and Panel Structures M265-M272 block
Page 28 of 29

<!-- Page 29 -->
Modern Kit Pattern Library
F35 Banded Identity Layouts M273-M280 signature-only
F36 Trim and Collar Systems M281-M288 block
EL1 3-4
EL2 4-6
EL3 7-10
EL4 11-14
E01 1,3,3,4,2,1
E02 2,2,4,1,1,1
E03 1,4,2,2,2,0
E04 2,3,3,5,3,1
E05 3,2,3,3,1,1
E06 1,5,1,4,2,0
E07 2,1,4,6,4,1
E08 3,4,2,2,6,0
E09 1,2,4,1,5,1
E10 2,5,2,4,1,1
E11 3,3,2,5,3,0
E12 1,4,3,3,4,1
E13 2,3,1,6,2,0
E14 4,4,2,2,1,1
E15 1,2,3,5,6,1
E16 3,5,2,4,2,0
E17 2,1,3,1,1,1
E18 4,3,3,3,3,1
E19 1,3,2,6,5,0
E20 2,4,4,2,2,1
E21 3,2,2,4,4,1
E22 1,5,3,5,1,0
E23 2,3,4,3,6,1
E24 3,4,1,1,3,1
SIG-CHE26H M193 M194 M282 M268
SIG-LIV26H M154 M281
SIG-MCI26H M257 M211 M285
SIG-PSG26H M265
SIG-FCB26H M273 M274 M283 M285 M235
SIG-COM26H M277 M281 M285 M207
Page 29 of 29

