# Real-Speech Corpus Benchmark

## Scope

This benchmark expands Pally's five-axis evaluation set with real English
speech from four public corpora. It keeps raw downloads out of version control
and stores only the cleaned, provenance-preserving fixtures and the scripts that
generate them.

The new labels are deterministic AI drafts. They are useful for comparing
analyzer candidates, but they are not independent human-review gold labels.
The prior NICT 600-row accepted-draft file remains separate and unchanged.

## Corpus Outputs

| Corpus | Extracted turns | Label candidates | Candidate groups | Label status |
|---|---:|---:|---:|---|
| CHiME-6 | 87,539 | 600 | 48 speakers | AI draft |
| HCRC Map Task | 20,686 | 500 | 117 dialogues | AI draft |
| Taskmaster-1 WoZ USER | 60,347 | 500 | 475 dialogues | AI draft |
| AMI meetings | 98,475 | 600 | 134 meetings, 136 speakers | AI draft |

Each candidate set has zero blank utterances and zero normalized-text
duplicates. The source-specific provenance fields are retained through draft
labeling, for example CHiME session/speaker/timing, HCRC dialogue role and move
label, and Taskmaster conversation/instruction/turn ID.

Files:

- `data/fixtures/chime6_utterances.jsonl`
- `data/fixtures/chime6_label_candidates_600.jsonl`
- `data/fixtures/chime6_labeled_draft_600.jsonl`
- `data/fixtures/hcrc_maptask_utterances.jsonl`
- `data/fixtures/hcrc_maptask_label_candidates_500.jsonl`
- `data/fixtures/hcrc_maptask_labeled_draft_500.jsonl`
- `data/fixtures/taskmaster1_woz_user_utterances.jsonl`
- `data/fixtures/taskmaster1_woz_user_label_candidates_500.jsonl`
- `data/fixtures/taskmaster1_woz_user_labeled_draft_500.jsonl`
- `data/fixtures/ami_utterances.jsonl`
- `data/fixtures/ami_label_candidates_600.jsonl`
- `data/fixtures/ami_labeled_draft_600.jsonl`
- `data/fixtures/axis_dataset_combined_real_speech_experimental.jsonl`
- `data/fixtures/real_speech_corpus_manifest.json`

## Sampling Rules

Candidates must have 3 to 45 words, a filler ratio at or below 0.30, no
unresolved annotations, no trailing filler or obvious incomplete ending, and
enough non-filler lexical content. Exact normalized duplicates are removed from
the sampled set, and no source group contributes more than 45 rows.

The buckets are `question`, `polite_request`, `short_reaction`,
`repair_disfluency`, `personal_statement`, and `narrative_description`.
CHiME-6 and Taskmaster reach their requested bucket quotas. HCRC has only three
polite-request candidates after filtering because its unscripted map-navigation
dialogue is dominated by instructions, checks, and acknowledgements; its quota
shortfall is intentionally filled from other usable buckets.

The sampler does not apply NICT's continuation-fragment rejection to these
corpora. Their records are already speaker turns, so a reply such as "Because I
work from home" may be complete in conversation. CHiME-specific bracketed event
markers and clipped `word-` fragments are removed only from the cleaned text;
their event markers remain in provenance.

## Labeling and Evaluation

The experimental evaluation file combines 338 existing seed labels, the NICT
600-row accepted-draft set, and four external draft sets for 3,137 rows total.
It is not a production training set until the external drafts receive human
review. The NICT accepted-draft file also copies draft values, so it is not an
independent blind human relabeling pass.

Leave-one-out evaluation on the 3,137 rows with word unigrams and bigrams:

| Analyzer | Avg MAE | Avg Spearman |
|---|---:|---:|
| rule | 10.05 | 0.30 |
| ML | **7.55** | 0.44 |
| hybrid | 7.95 | **0.45** |

The source-group holdout keeps a whole dialogue or meeting in either training
or test (`2,889` train / `248` test): ML has the lowest average MAE (`7.62`
vs. hybrid `7.86`), while both have average Spearman `0.45`. ML is now a close
candidate, but not ready to replace hybrid because the labels are AI drafts and
the rank result is not a clear independent win.

Run extraction, sampling, draft labeling, combination, and evaluation from the
repository root:

```powershell
.\.venv\Scripts\python.exe scripts\extract_chime6.py
.\.venv\Scripts\python.exe scripts\extract_hcrc_maptask.py
.\.venv\Scripts\python.exe scripts\extract_taskmaster1_woz.py
.\.venv\Scripts\python.exe scripts\extract_ami.py

.\.venv\Scripts\python.exe scripts\sample_real_speech_label_candidates.py `
  --input data\fixtures\chime6_utterances.jsonl `
  --output data\fixtures\chime6_label_candidates_600.jsonl --size 600

.\.venv\Scripts\python.exe scripts\draft_label_nict_jle_candidates.py `
  --input data\fixtures\chime6_label_candidates_600.jsonl `
  --output data\fixtures\chime6_labeled_draft_600.jsonl

.\.venv\Scripts\python.exe scripts\build_real_speech_axis_dataset.py `
  --labels data\fixtures\nict_jle_labeled_human_600.jsonl `
  data\fixtures\chime6_labeled_draft_600.jsonl `
  data\fixtures\hcrc_maptask_labeled_draft_500.jsonl `
  data\fixtures\taskmaster1_woz_user_labeled_draft_500.jsonl `
  data\fixtures\ami_labeled_draft_600.jsonl `
  --output data\fixtures\axis_dataset_combined_real_speech_experimental.jsonl

$env:PALLY_AXIS_DATASET='data\fixtures\axis_dataset_combined_real_speech_experimental.jsonl'
.\.venv\Scripts\python.exe ai\evaluate_axis_analyzers.py --word-ngram-max 2
.\.venv\Scripts\python.exe ai\evaluate_axis_analyzers.py --word-ngram-max 2 --mode source-group-holdout
Remove-Item Env:\PALLY_AXIS_DATASET
```

## License Gate

- CHiME-6 is listed as CC BY-SA 4.0 by [OpenSLR SLR150](https://www.openslr.org/150/).
- Taskmaster-1 is CC BY 4.0 according to its [official README](https://github.com/google-research-datasets/Taskmaster/blob/master/TM-1-2019/README.md).
- AMI manual annotations, including the orthographic transcription and dialogue-act annotations, are CC BY 4.0 according to the [official download page](https://groups.inf.ed.ac.uk/ami/download/).
- The current [HCRC download page](https://groups.inf.ed.ac.uk/maptask/maptasknxt.html) says CC BY 4.0, but the downloaded v2.1 archive's `00README.txt` and `00LICENSE.html` state CC BY-NC-SA 2.5. Treat the locally used HCRC package as non-commercial until HCRC confirms the applicable license in writing.

CHiME-6 and HCRC also carry participant-privacy and attribution obligations;
keep the raw downloads local, retain source metadata, and obtain a license review
before any public or commercial model release.

## Analyzer Handoff

The backend already calls `get_axis_analyzer()` through its adapter and applies
`shape_reply()` after Gemini response generation. `PALLY_AXIS_ANALYZER` can be
set to `rule`, `ml`, or `hybrid`; `PALLY_AXIS_DATASET` now resolves relative to
the repository root so the same fixture path works when the backend starts from
its own directory.

Keep `rule` as the runtime default. ML with word bigrams is the primary
single-model candidate; hybrid remains the fallback candidate until a frozen,
independent human-reviewed test set shows ML is at least as strong on rank
separation as well as absolute error.
