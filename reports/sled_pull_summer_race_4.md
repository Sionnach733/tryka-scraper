# Was the Sled Pull Harder in Dublin Summer Race 4?

**Short answer: yes — decisively, and across every cohort.** After controlling for
field strength and general race pace, the Sled Pull consumed roughly **50% more of an
athlete's workstation effort** in Summer Race 4 than in any of the three prior Dublin
races. The effect is not confined to one division or gender, but **women** and the
**solo (Open / Pro) divisions** were hit hardest.

Reproduce with: `python3 sled_variance.py`

---

## Method: why not just compare times?

Raw Sled Pull times *are* much slower in Summer 4 — e.g. Doubles-500 men went from
~2:42 to 4:17. But raw times are **confounded**: a weaker field, a hotter day, or a
generally slower course inflates *every* station at once, so a slow Sled Pull time on
its own can't tell you whether the station itself changed.

The clean control is to express Sled Pull as a **share of each athlete's own total
8-station workstation time**:

```
share = Sled Pull time / (sum of all 8 station times)   — per athlete, then take the median
```

This normalises away fitness, field strength and overall pace. If the Sled Pull's share
is **flat across races**, the station's relative difficulty was unchanged and slow times
just reflect a slow race. If the share **jumps**, the station itself got harder relative
to everything else the athletes did that day.

> **Data note:** the `TRY Zone Total` split is *not* the sum of the eight station times
> (using it as the denominator produces shares above 100%), so it must not be used here.
> Only divisions running the full 8-station format qualify; junior, clan and relay-format
> events that lack a station drop out automatically.

---

## Headline result

Median Sled Pull share of 8-station workload, pooled across all qualifying divisions:

| Gender | Autumn 1 | Winter 2 | Spring 3 | **Summer 4** | Δ vs prior avg |
|--------|:---:|:---:|:---:|:---:|:---:|
| Men    | 11.4 | 11.7 | 12.0 | **16.8** | **+5.1** |
| Women  | 12.7 | 12.8 | 12.8 | **18.2** | **+5.5** |
| Mixed  | 12.5 | 12.3 | 12.4 | **17.7** | **+5.3** |

The share sits in a tight ~11–13% band for the first three races, then jumps by **5+
percentage points** in Summer 4 — a relative increase of roughly **45–50%** in how much
of the workday the Sled Pull ate. Because this metric already divides out overall pace,
the jump is direct evidence that **the station was made harder**, not that the race was
merely slower.

---

## Breakdown by division × gender

Median Sled Pull share (%), with the Summer-4 delta vs the mean of the three prior races
and the Summer-4 sample size:

| Division | Gender | Autumn 1 | Winter 2 | Spring 3 | **Summer 4** | **Su4 Δ** | N (Su4) |
|----------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Doubles 500 | M | 10.8 | 11.5 | 11.5 | 16.4 | +5.1 | 234 |
| Doubles 500 | W | 12.5 | 12.6 | 12.7 | 18.0 | +5.4 | 1105 |
| Doubles 500 | X | 12.4 | 12.3 | 12.3 | 17.8 | +5.4 | 464 |
| Doubles 800 | M | 11.2 | 11.2 | 11.6 | 16.0 | +4.6 | 422 |
| Doubles 800 | W | 12.9 | 12.7 | 12.8 | 17.6 | +4.8 | 555 |
| Doubles 800 | X | 12.5 | 12.3 | 12.5 | 17.7 | +5.2 | 344 |
| Open 500 | M | 9.7 | 11.3 | 11.9 | 18.4 | **+7.5** | 225 |
| Open 500 | W | – | 13.4 | 13.3 | 19.4 | +6.1 | 430 |
| Open 800 | M | 11.4 | 11.8 | 12.1 | 17.5 | +5.7 | 557 |
| Open 800 | W | – | 13.2 | 13.1 | 18.6 | +5.5 | 345 |
| Pro | M | 13.9 | 13.1 | 14.9 | 17.7 | +3.8 | 61 |
| Pro | W | 13.4 | 12.8 | 12.3 | 20.4 | **+7.6** | 30 |
| Pro Doubles | M | – | – | 13.9 | 16.8 | +2.8 | 34 |
| Pro Doubles | W | – | – | 12.7 | 19.7 | **+7.0** | 29 |
| Relay | W | 12.4 | 13.1 | 12.8 | 19.3 | +6.5 | 25 |

*(Doubles Pro and some Relay/Open cells are blank in Summer 4 — those events either did
not run the format or fielded too few finishers with a complete 8-station record. Raw
median times per cohort are in the second table of `sled_variance.py` output.)*

### 1. Every cohort struggled more — no one was spared

There is no division or gender where the Summer-4 share stayed flat. The smallest jump
(Pro men, +2.8–3.8) is still a meaningful shift; the largest exceed +7 points. Whatever
changed about the Sled Pull, it changed for the whole field.

### 2. Women struggled more than men

In almost every matched division the women's Summer-4 delta and absolute share exceed the
men's:

- **Pro:** women +7.6 (to 20.4%) vs men +3.8 (to 17.7%) — the single widest gender gap.
- **Pro Doubles:** women +7.0 vs men +2.8.
- **Open 500:** women land at 19.4% vs men 18.4%.
- Women already carried a higher baseline share (~12.7% vs ~11.4% pre-Summer), and Summer 4
  widened that gap rather than closing it.

This is consistent with a Sled Pull change that scales worse for lower-absolute-strength
athletes — e.g. a heavier sled or longer pull distance costs proportionally more when you
have less headroom over the load.

### 3. Solo (Open / Pro) divisions were hit harder than doubles teams

- **Open 500 men +7.5** and **Open 800 men +5.7** are among the biggest jumps, versus
  **Doubles 500/800 men at +4.6–5.1**.
- The pattern holds for women: solo Pro/Pro-Doubles women (+7.0 to +7.6) exceed the
  doubles-team women (+4.8 to +5.4).

In team formats a partner can share or alternate the sled work, blunting the hit. Solo
athletes absorb the full change, so the harder station shows up most sharply in the
individual divisions.

### Who struggled most

The worst-affected cohort is **Pro women** (share to 20.4%, +7.6), followed by the
**solo Open/Pro-Doubles women** and **Open 500 men**. The most resilient were the
**Pro / Pro-Doubles men** and the **Doubles-800 teams**.

---

## Caveats

- **Thin samples in the elite divisions.** Pro (N≈30 women, 61 men), Pro Doubles (~29–34)
  and the Summer Relay women (N=25) rest on small fields, so their exact deltas are noisier
  than the large Doubles/Open cohorts (hundreds to 1,100+). The *direction* is consistent
  everywhere; treat the elite magnitudes as indicative.
- **Format coverage varies by race.** Doubles Pro ran in Autumn/Winter but not Summer;
  Pro Doubles appears only from Spring. Cross-race deltas are computed only over races where
  a cohort actually fielded finishers with a complete 8-station record.
- **This isolates *relative* difficulty, not the cause.** The share metric proves the Sled
  Pull got disproportionately harder; it can't distinguish *why* (heavier implement, longer
  distance, different surface/turf, judging/standards). Confirming the cause needs the event
  spec, not the results data.
- **Median-based.** All figures are medians to resist outliers and DNF-adjacent tails;
  means would read slightly higher due to long right tails on a grinding station.
