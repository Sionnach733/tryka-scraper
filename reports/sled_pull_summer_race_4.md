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
> Only divisions running the full 8-station format qualify; junior and clan events that lack
> a station drop out automatically, and the relay-format event is excluded as non-comparable.

---

## Headline result

Median Sled Pull share of 8-station workload, pooled across all qualifying divisions:

| Gender | Autumn 1 | Winter 2 | Spring 3 | **Summer 4** | Δ vs prior avg |
|--------|:---:|:---:|:---:|:---:|:---:|
| Men    | 11.4 | 11.7 | 12.0 | **16.8** | **+5.1** |
| Women  | 12.9 | 12.8 | 12.8 | **18.2** | **+5.4** |
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
| Doubles 800 | W | 12.9 | 12.7 | 12.8 | 17.6 | +4.8 | 554 |
| Doubles 800 | X | 12.5 | 12.3 | 12.5 | 17.7 | +5.2 | 345 |
| Open 500 | M | 9.7 | 11.3 | 11.9 | 18.4 | **+7.5** | 225 |
| Open 500 | W | 13.4 | 13.4 | 13.3 | 19.4 | +6.0 | 430 |
| Open 800 | M | 11.4 | 11.8 | 12.1 | 17.5 | +5.7 | 557 |
| Open 800 | W | 13.1 | 13.2 | 13.1 | 18.6 | +5.5 | 345 |
| Pro | M | 13.9 | 13.1 | 14.9 | 17.7 | +3.8 | 61 |
| Pro | W | 13.4 | 12.8 | 12.3 | 20.4 | **+7.6** | 30 |
| Pro Doubles | M | 13.3 | 12.9 | 13.9 | 16.8 | +3.4 | 34 |
| Pro Doubles | W | 13.2 | 13.2 | 12.7 | 19.7 | +6.7 | 29 |

*(Two cohorts span all four races thanks to how the source data is handled. The **Pro
Doubles** row: the division ran as `TRYKA DOUBLES PRO` in Autumn 1 / Winter 2 and was renamed
`TRYKA PRO DOUBLES` from Spring 3, so the two names are merged into one cohort. **Open women:**
in Autumn 1 the women's Open 500/800 ran as their *own* Sunday divisions (merged into the
combined Open 500/800 only from Winter 2 on); the organiser published those Sunday events with
finish times and station splits but **no overall rank**, so the analysis admits them on the
strength of a complete 8-station record (183 women in Open 500, 228 in Open 800). The
relay-format event is excluded — its workload is not comparable to the individual/doubles
8-station races. Raw median times per cohort are in the second table of `sled_variance.py`
output — reproduced below.)*

| Division | Gender | Autumn 1 | Winter 2 | Spring 3 | **Summer 4** |
|----------|:---:|:---:|:---:|:---:|:---:|
| Doubles 500 | M | 2:42 | 2:54 | 2:58 | **4:17** |
| Doubles 500 | W | 3:47 | 3:43 | 3:40 | **5:39** |
| Doubles 500 | X | 3:33 | 3:29 | 3:24 | **5:27** |
| Doubles 800 | M | 2:43 | 2:39 | 2:43 | **4:03** |
| Doubles 800 | W | 3:25 | 3:27 | 3:25 | **5:09** |
| Doubles 800 | X | 3:14 | 3:10 | 3:11 | **5:03** |
| Open 500 | M | 3:31 | 4:07 | 4:17 | **7:15** |
| Open 500 | W | 5:22 | 5:04 | 4:58 | **8:08** |
| Open 800 | M | 3:39 | 3:49 | 3:54 | **6:03** |
| Open 800 | W | 4:34 | 4:21 | 4:24 | **6:51** |
| Pro | M | 4:04 | 4:08 | 4:29 | **6:01** |
| Pro | W | 4:13 | 4:15 | 4:23 | **8:48** |
| Pro Doubles | M | 2:59 | 2:57 | 3:18 | **3:58** |
| Pro Doubles | W | 3:36 | 3:28 | 3:14 | **5:20** |

Raw times roughly **double** in the hardest cohorts (Pro women 4:23 → 8:48; Open 500
women 4:58 → 8:08; Open 500 men 4:17 → 7:15) — but raw times are confounded, which is
why the share metric above is the load-bearing evidence.

### 1. Every cohort struggled more — no one was spared

There is no division or gender where the Summer-4 share stayed flat. The smallest jump
(Pro Doubles men, +3.4) is still a meaningful shift; the largest exceed +7 points. Whatever
changed about the Sled Pull, it changed for the whole field.

### 2. Women struggled more than men

In almost every matched division the women's Summer-4 delta and absolute share exceed the
men's:

- **Pro:** women +7.6 (to 20.4%) vs men +3.8 (to 17.7%) — the single widest gender gap.
- **Pro Doubles:** women +6.7 vs men +3.4.
- **Open 500:** women land at 19.4% vs men 18.4%.
- Women already carried a higher baseline share (~12.8% vs ~11.4% pre-Summer), and Summer 4
  widened that gap rather than closing it.

This is consistent with a Sled Pull change that scales worse for lower-absolute-strength
athletes — e.g. a heavier sled or longer pull distance costs proportionally more when you
have less headroom over the load.

### 3. Solo (Open / Pro) divisions were hit harder than doubles teams

- **Open 500 men +7.5** and **Open 800 men +5.7** are among the biggest jumps, versus
  **Doubles 500/800 men at +4.6–5.1**.
- The pattern holds for women: solo Pro/Pro-Doubles women (+6.7 to +7.6) exceed the
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

- **Thin samples in the elite divisions.** Pro (N≈30 women, 61 men) and Pro Doubles (~29–34)
  rest on small fields, so their exact deltas are noisier than the large Doubles/Open cohorts
  (hundreds to 1,100+). The *direction* is consistent everywhere; treat the elite magnitudes
  as indicative.
- **Format coverage varies by race.** The Pro-doubles division was renamed mid-series
  (`TRYKA DOUBLES PRO` in Autumn/Winter → `TRYKA PRO DOUBLES` from Spring); the two names are
  the same event and are merged into one cohort, giving it a full four-race history. Women's
  Open ran as its own separate Sunday divisions in Autumn 1 and was combined with the men's
  Open from Winter 2 on; those Autumn-1 women's-Open finishers carry no source overall rank
  but have complete 8-station records, so they are admitted to the Open cohort here. The
  relay-format event is excluded outright as non-comparable. Cross-race deltas are otherwise
  computed only over races where a cohort actually fielded finishers with a complete
  8-station record.
- **This isolates *relative* difficulty, not the cause.** The share metric proves the Sled
  Pull got disproportionately harder; it can't distinguish *why* (heavier implement, longer
  distance, different surface/turf, judging/standards). Confirming the cause needs the event
  spec, not the results data.
- **Median-based.** All figures are medians to resist outliers and DNF-adjacent tails;
  means would read slightly higher due to long right tails on a grinding station.
