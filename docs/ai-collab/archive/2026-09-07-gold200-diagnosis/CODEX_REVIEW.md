# Codex Review - Round 2 (Critical Review)

> Scope: `CONTEXT.md`, `CLAUDE_REVIEW.md`, and the current implementation/data
> paths were read. No analyzer, dataset, or evaluation code was changed. Counts
> below are static audit results from the frozen files on 2026-09-07.

## Bottom line

Claude's main direction is plausible: the current AI-draft teacher is not good
enough evidence for making ML the runtime default, and adding more rows with
the same teacher is unlikely to repair every axis. However, the current
gold-200 comparison is **not yet an acceptance-gate-quality estimate**. Two
independent validity problems must be separated before attributing the result
primarily to the rubric:

1. At least 72 of 200 gold rows share a `source_group` with the 3,137-row ML
   training set, despite zero normalized exact-text overlaps. Another 68 NICT
   rows cannot be group-checked because that field was dropped from its active
   training records.
2. The 200 target labels combine two reviewer regimes whose assignment is
   strongly confounded with source.

Therefore, keep `rule` as the default and do not decide between ML and hybrid
from the current aggregate gold numbers alone.

## Findings

### 1. [High] Gold-200 is not source-group held out from the active 3,137-row training set

`sample_ml_transition_candidates.py` excludes only normalized utterance text
from `axis_dataset_combined_real_speech_experimental.jsonl`. It partitions the
new gold and train candidate pools by group, but it does not exclude source
groups already present in the pre-existing 3,137-row training set.

Static audit result:

| Check | Result |
|---|---:|
| normalized exact gold/training utterance overlap | 0 / 200 |
| overlapping `(source, source_group)` values | 44 |
| gold rows in a confirmed overlapping group | 72 / 200 (36%) |
| affected gold sources | AMI 65, Taskmaster 7 |
| largest number of training rows from one overlapping group | 12 |
| training rows without `source_group` | all 600 NICT rows, plus 338 seed rows |

This is not duplicate-text leakage, and the TF-IDF model has no explicit group
feature. It is still a meaningful conversational/domain leakage risk: meeting
topic, participants, local vocabulary, and dialogue style can occur on both
sides. It contradicts the acceptance gate's "source-group-held-out" premise.

The missing NICT provenance makes the situation less certain, not safer. Gold
NICT rows retain identifiers such as `file00396`, but the 600 active NICT
training rows retain only `source_line`. Consequently neither the audit nor
`split_by_source_group()` can hold out NICT interview groups reliably; the
evaluator falls back to one pseudo-group per utterance when `source_group` is
empty. The current gold result remains useful as a diagnostic, but cannot by
itself prove a gate decision.

**Minimum discriminating test:** report ML/rule/hybrid separately for the 72
confirmed-overlap rows, the 60 confirmed-nonoverlap AMI/Taskmaster rows, and
the 68 NICT rows whose group status is unknown. Then, before a future gate run,
restore/retain a comparable NICT group key and select from the untouched 400
gold candidates only groups absent from the actual training dataset.

### 2. [High] Reviewer regime and source are confounded in the gold target

The first 100 rows are `reviewer-avg`; the next 100 are `reviewer-01`.
Their source composition is not mixed:

| Reviewer regime | Rows | Source composition |
|---|---:|---|
| `reviewer-avg` | 100 | AMI 67, NICT 33 |
| `reviewer-01` | 100 | Taskmaster 65, NICT 35 |

The effect is visible in the stored targets. `reviewer-01` assigned Humor 0 to
all 100 rows (zero standard deviation), whereas `reviewer-avg` has Humor
values from 0 to 55. The two regimes also differ substantially on the other
axes. There are no individual component ratings retained for `reviewer-avg`,
so inter-rater agreement and calibration cannot be calculated.

This means a source-specific model result can be mistaken for reviewer-scale
differences, and vice versa. It also weakens the claim that the observed Humor
Spearman is solely a teacher-rubric problem.

**Minimum discriminating test:** have the two reviewer protocols independently
score the same balanced, source-mixed subset (for example 30-50 rows), retain
the individual ratings, and calculate per-axis agreement plus mean-scale
differences. Do not alter the frozen current CSV while doing this.

### 3. [High] The `sample_bucket` caveat is narrower than Claude states, but more consequential for pipeline fidelity

`diagnose_gold_vs_ai_draft.py` calls:

```python
draft_axes({"utterance": row["utterance"]})
```

All gold rows therefore use the default `personal_statement` bucket. For this
exact diagnostic only, the bucket effect is a constant **+15 Intimacy**. It
does not change the rank, standard deviation, or shape of that direct output;
it also does not shift every axis as the script comment suggests. Accordingly,
the reported Intimacy bias (+27.39) is inflated by 15 points, while the
default-bucket path does not directly alter Formality, Energy, Humor, or
Curiosity in that run.

That limited statement does **not** make the diagnostic a faithful replay of
the actual draft-label pipeline. In the 3,137-row training set, 2,799
real-speech rows have varied `sample_bucket` values. Reconstructing buckets
for gold can change a row's output by, for example, `question` (+48 Curiosity,
+5 Formality), `polite_request` (+30 Curiosity, +24 Formality, +6 Intimacy),
or `repair_disfluency` (-8 Formality, +4 Energy, +6 Intimacy, +3 Humor).
Those are row-varying changes, so they can change rank correlation, MAE, and
score dispersion. Curiosity is especially exposed: its apparent 0.83
Spearman must not be called "nearly OK" until this sensitivity is checked.

There is no original gold `sample_bucket`; a reconstruction with
`classify_bucket()` is still heuristic, not ground truth. The stratified gold
candidates also have no `move_label`, and 133/200 have no `annotation_events`,
so the reconstruction is primarily text based. It is nevertheless the right
small test of sensitivity.

**Minimum discriminating test:** using the original
`ml_transition_gold_stratified_candidates_200.jsonl`, compare the current
default result with `sample_bucket=classify_bucket(candidate)` for every row.
Report per-axis Spearman, MAE, bias, SD ratio, threshold confusion, and the
number of bucket changes. Label the result "bucket sensitivity analysis," not
"the true teacher score."

### 4. [Medium] The evidence supports real-speech label scarcity, not a universal Energy ceiling

The direct default-bucket gold run contains no Energy score at least 50. That
is a useful warning, but "structural ceiling" is too strong: `draft_axes()`
can produce values above 50, and the 3,137-row experimental set contains 126
such Energy labels. The distribution is still concerning: only 15 of those
126 come from real-speech sources; 111 come from the 338 LLM seed rows.

Thus the supported conclusion is narrower and actionable: this rubric plus
the sampled real-speech data supplies almost no high-Energy supervision. The
same pattern appears for Humor (only 5 real-speech rows at 40 or above). More
real-speech rows labeled by the unchanged rubric will probably preserve that
imbalance. It does not prove that text-defined Energy is intrinsically
unlearnable.

The gold reviewers saw transcript/context rather than acoustic prosody. An
"audio is required" conclusion would describe a different target unless the
annotation protocol is deliberately changed to include audio.

### 5. [Medium] "Human-reviewed" training provenance needs precise wording

In the combined training file, 600 NICT rows have `label_status` set to
`human_reviewed`, but their stored `labeler` is `codex_accept_draft_per_user`.
The remaining 2,199 real-speech rows are explicitly
`ai_draft_needs_human_review`. Unless a separate per-row human numeric-score
record exists, the 600 rows should be described as *accepted AI drafts*, not
independent human-scored gold labels. This matters for any claim that the
training data already contains human supervision.

Likewise, 175 half-point values present in the gold review CSV are silently
truncated by `int(float(value))` when producing the JSONL used by evaluation;
the evaluated JSONL has no fractional scores. The numerical effect is bounded
by 0.5 per label, but it introduces avoidable ties and makes the documented
"0.5-unit average" claim false for the actual evaluator input. Decide and
document a rounding/precision policy before treating future metrics as final.

### 6. [Medium] More human labels are necessary evidence, but not a standalone solution

The pending 120-row set labels only Energy and Curiosity, and the current ML
trainer has no partial-label support. Even after that support exists, those
rows cannot establish an all-five-axis ML default or repair Humor/Intimacy/
Formality supervision. Use them as a targeted calibration/learning-curve
experiment, not as proof that the five-axis gate has been met.

## Agreement and disagreement with Round 1

**Agree**

- The current data does not justify changing the runtime default from `rule`
  to `ml`; the published gate already fails on the current aggregate result.
- Repeating the same draft rubric over more utterances is unlikely to create
  missing high-Energy or high-Humor supervision.
- Humor, Energy, and Intimacy deserve focused diagnosis before spending a large
  annotation budget.

**Qualify / disagree**

- The default-bucket diagnostic preserves ranks only for its own artificial
  all-`personal_statement` input. It cannot validate the rank behavior of the
  bucketed teacher that created training labels.
- "Information-free" and "structural ceiling" are stronger claims than the
  current evidence establishes. They are plausible hypotheses, not final
  diagnoses, until bucket sensitivity and reviewer effects are measured.
- Current gold aggregate metrics cannot be treated as a clean source-group
  holdout: 36% of rows have confirmed shared training groups and 68 NICT rows
  cannot be checked with the active training provenance.
- More data alone is not the decision variable. The next value comes from an
  independent evaluation boundary, a consistent human scoring protocol, and
  targeted coverage of underrepresented score ranges.

## Recommended decision order for Round 3

1. Run the read-only bucket-sensitivity analysis above.
2. Split the existing gold performance by training-group overlap; record it as
   diagnostic evidence only.
3. Resolve reviewer calibration with a small shared, source-balanced rescoring
   set and preserve individual ratings.
4. Define the score precision policy, then regenerate/re-evaluate only after a
   later explicit implementation decision.
5. Build the next acceptance test from source groups absent from the active
   training set. Only then use additional human labels to compare ML, hybrid,
   and rule against the acceptance gate.
