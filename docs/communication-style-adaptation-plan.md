# Communication-Style Research Plan

## Product Boundary

Pally has two different problems that must remain separate:

1. The five-axis analyzer estimates a user's communication state for an utterance.
2. An adaptation policy decides whether Pally should mirror, partially mirror,
   complement, or retain its own response style.

The current ML transition covers the first problem only. No study cited in the
research notes justifies making full user-agent matching the production default.

## Data Contract

Every real-speech extraction now preserves, when a corpus provides it:

```text
source, source_group, source_record_id
conversation_id, speaker or speaker_id, turn_index
previous_turn, previous_turn_speaker
utterance
next_turn, next_turn_speaker
audio reference or timing metadata when available
```

This preserves the information needed to compare an utterance-only model with a
context model without rebuilding the source corpora. Review CSVs expose only
the utterance and adjacent text context; source, speaker, group, sampling
bucket, and model metadata remain hidden from annotators.

## Modeling Sequence

### Phase 1: Measurement

- Complete the 200-row, five-axis blind gold review and the 120-row Energy and
  Curiosity active review.
- Keep source-group and speaker/conversation boundaries intact in every split.
- Treat the 120-row set as partial Energy/Curiosity labels until the trainer
  supports per-axis partial supervision.

### Phase 2: Feature And Context Ablations

Evaluate each addition on the frozen human-reviewed gold set, not on its own
training labels:

1. Word 1-2 grams.
2. Add character n-grams.
3. Add observable text-form features: punctuation, length, contractions, and
   filler counts.
4. Add sentiment, arousal, and subjectivity proxies only if their definitions
   are fixed before evaluation.
5. For Curiosity, compare current utterance alone against previous-turn plus
   current-utterance context.
6. For Energy, separately test the text-only ceiling against speech rate,
   pitch, intensity, pause, and laughter features where the audio license and
   source data permit their use.

Big Five traits are not labels or aliases for Pally's five communication axes.
They may be used only as an external construct-validation reference.

### Phase 3: User State

`ai/style_state.py` now defines a slow-moving `baseline` and a faster
`current` state, plus normalized style distance. The module is intentionally
not wired into response adaptation yet. Baseline answers how a user generally
communicates; current state answers how the user is communicating in the recent
window.

### Phase 4: Adaptation Experiment

Before changing default Pally behavior, collect a separate interaction-outcome
dataset with explicit conditions: fixed style, partial mirroring, and one or
more complementary policies. Record comfort, affinity, distinctiveness,
engagement, learner accommodation, and learning outcome. Compare trajectory
variables, including user-agent style distance, rather than assuming that a
smaller distance is universally better.

The `partial_mirror_target()` helper is an experimental control only. It has a
bounded axis shift so a temporary user mood cannot fully replace Pally's stable
tutor persona.
