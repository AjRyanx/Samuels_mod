# Season Lifecycle & Career Progression

This document explains how seasons progress in Master League, how AI multi-year contracts function, and how the player's storyline opt-in rules operate across multi-season careers.

---

## 1. Season Chronology & Date Mapping

In **SP Football Life 2027** (PES 2021 engine), the Master League calendar starts in **July 2026**.

The season identifier (`SEASON`) is named after the calendar year in which the season **concludes**:

| Calendar Date Range | Master League Phase | Mod Season ID | AI Opponent Kits | User Club Kits |
| :--- | :--- | :--- | :--- | :--- |
| **July 2026 – May 2027** | Season 1 (Inaugural) | `SEASON = 2027` | **Authentic Licensed** | Authentic (until deal signed) |
| **June 2027 – Aug 2027** | Season 1/2 Pre-Season | `SEASON = 2028` | Pre-Season Transition | Sponsor Office window open |
| **Aug 2027 – May 2028** | Season 2 (Championship) | `SEASON = 2028` | **Dynamic Sponsor Kits** | Dynamic (or Sponsorless if expired) |
| **June 2028 – Aug 2028** | Season 2/3 Pre-Season | `SEASON = 2029` | Deal Renewal Window | Sponsor Office window open |
| **Aug 2028 – May 2029** | Season 3 (Continental) | `SEASON = 2029` | **Dynamic Sponsor Kits** | Dynamic (or Sponsorless if expired) |

---

## 2. AI Opponent Sponsorship Mechanics

### 2.1 Multi-Year Contracts
Every AI club in `clubs.csv` (all 587 teams) is assigned a realistic multi-year contract:
- **Contract Duration**: 2 or 3 seasons, determined deterministically by club ID:
  $$\text{duration} = \begin{cases} 2, & \text{if } \text{club\_id} \equiv 0 \pmod 2 \\ 3, & \text{otherwise} \end{cases}$$
- **Contract Epoch**:
  $$\text{cycle\_start} = 2026 + \left\lfloor \frac{\text{season} - 2026}{\text{duration}} \right\rfloor \times \text{duration}$$
- **Sponsor Brand Selection**:
  Drawn from the 140 commercial brands in `content/KitGenerator/logos/` using a deterministic hash of the club ID and contract cycle start year.

### 2.2 Season 1 Gating Rule
In Season 1 (`SEASON < 2028`), the Sider module suppresses dynamic kits for all CPU opponents (`tid ~= cid` yields `nil`). Kitserver serves their original licensed kits (e.g. Real Madrid wearing Emirates, Barcelona wearing Spotify, Arsenal wearing Emirates).

When the calendar enters Season 2 (`SEASON >= 2028`), the module automatically serves the dynamic kit set compiled for that cycle.

---

## 3. Human Managed Club: Storyline Opt-In

### 3.1 Initial State (Authentic Default)
When starting a career:
- `opted_in.txt` contains no record for your club.
- `KitGenerator.lua` yields `nil` for your team ID.
- Your club wears authentic licensed kits with original sponsors.

### 3.2 Transition to Dynamic Kits
1. In the pre-season (June–August), open the **Sponsor Office** (Mod Menu **F1** or **F7**).
2. Review offers tailored to your club's tier (`big`, `mid`, `small`).
3. Sign an offer. The contract details are saved to `active_deal.txt` and your club is marked in `opted_in.txt`.
4. The Python watcher generates and deploys your new kits with the signed sponsor's logo and kit manufacturer branding.

### 3.3 Contract Expiration & Off-Season Previews
- When your multi-year contract reaches its final year and expires, your club enters the off-season.
- During the off-season pre-signing window, your team wears a **clean, sponsorless dynamic kit** rather than reverting to years-old default licensed sponsors.
- Once you sign a new sponsor in the menu, the new sponsor's logo is stamped on the chest.
- If you ever wish to return to default kits, the Sponsor Office provides a **"Revert to authentic kits"** button.
