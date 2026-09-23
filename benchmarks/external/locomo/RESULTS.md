# ContextFlow vs. LoCoMo — a real external benchmark, not a self-authored one

Unlike `benchmarks/datasets/acme_support_v1.yaml` (ContextBench v0.1,
which we wrote ourselves and disclosed as synthetic), this evaluates
ContextFlow against **LoCoMo** (Maharana et al., ACL 2024,
[snap-research/locomo](https://github.com/snap-research/locomo)) — a
real, externally-authored, widely-cited benchmark that Mem0, Zep,
Letta, and other competitors in this space also report numbers
against. Run it yourself: `python benchmarks/external/locomo/run_locomo_eval.py`
(downloads the dataset automatically; see the script's docstring for
the full methodology, and the license note at the bottom of this file
before you do anything with the downloaded data beyond local evaluation).

## Results (run against this codebase, this session)

### Current code (after the retrieval fixes below)

```
                  hash (default)   ollama nomic-embed-text   published comparable
Recall@5              26.7%               58.3%                    93.9%
Recall@10             37.6%               65.4%                      --
MRR                   0.211               0.508                      --
NDCG@5                0.202               0.496                      --

Per category (Recall@5):
  single-hop (n=841)  32.1%   64.1%
  temporal   (n=321)  28.3%   68.3%
  multi-hop  (n=282)   8.5%   29.7%
```

What changed (all general retrieval fixes, none LoCoMo-specific):
retrieval scores no longer leak between queries via the stored objects;
the reranker ranks on the normalized fused hybrid score instead of
mixing raw cosine and BM25 scales; BM25 tokenization drops punctuation
and stopwords and folds possessives/plurals; nomic's `search_query:` /
`search_document:` prefixes are applied. To guard against overfitting,
these were tuned on conversations 0-1 only; on the 8 held-out
conversations (1,224 questions) Recall@5 was 58.3%, the same as the
tuning split (58.4%). `mxbai-embed-large` was also tried and scored
slightly lower (57.3% vs 58.4% on the tuning split).

### Before those fixes

Four configurations, same code, same dataset, same 1,444 evaluable
questions:

```
                  hash       spacy (md)    spacy (lg)    ollama
                (default)     (local)       (local)     nomic-embed-text
Recall@5          8.5%        15.8%         27.3%          44.5%
Recall@10        14.5%        25.7%         40.7%          61.0%
MRR              0.059        0.105         0.168          0.284
NDCG@5           0.055        0.102         0.173          0.298

Per category (Recall@5):
  single-hop (n=841)   10.5%   19.7%   32.2%   54.4%
  temporal   (n=321)    6.8%   15.4%   32.5%   43.3%
  multi-hop  (n=282)    4.4%    4.8%    6.9%   16.3%
```

Reproduce: `--provider hash` / `--provider spacy [--model en_core_web_lg]`
/ `--provider ollama` (after `ollama pull nomic-embed-text`). The Ollama
run took 11.5 minutes end to end on a CPU-only 8 GB Windows laptop,
using the batched `/api/embed` path for ingest.

**Correction:** earlier versions of this file (and of
`run_locomo_eval.py`) had the single-hop and multi-hop labels swapped.
LoCoMo category 1 is multi-hop (98% of its questions cite 2+ evidence
turns) and category 4 is single-hop (5%). The rows above are relabeled;
the underlying numbers for hash/spaCy are unchanged.

## Did we beat the benchmark? No — and here's the honest reasoning why

**Update:** a trained sentence encoder (lever 1 below) was since tested
via a local Ollama `nomic-embed-text`. It lifted Recall@5 to **44.5%**, and
the retrieval fixes above then took it to **58.3%**, with no API key. Single-hop questions now find their evidence turn in the top 5 more
than half the time. Multi-hop (16.3%) is still weak: each of those
questions needs ~3 separate turns, which is what lever 2 (fact
extraction) addresses. The analysis below predates that run.

Going from the hash placeholder to `en_core_web_lg` word vectors is a
**real, substantial, measured improvement: roughly 3.2x on Recall@5**
(8.5% -> 27.3%), achieved with zero API keys and zero external services.
That's genuine progress, not a rounding change -- temporal and multi-hop
questions in particular went from "barely working" to "finding the
right turn about a third of the time."

It is still **far** from competitive. 27.3% vs. 93.9% is not a close
gap you'd expect one more tuning pass to close. Two heuristic levers
were also tried and gave only marginal, mixed results (session-date
prefixing, small context-window enrichment around each turn) --
confirming the bottleneck is fundamentally embedding *quality*, not
missing metadata or chunk boundaries.

**What it would actually take to close the rest of the gap, and why none
of it was available in this session:**

1. **A trained sentence encoder** (sentence-transformers, or an
   API-based embedding like OpenAI/Cohere) instead of averaged static
   word vectors. `en_core_web_lg`'s GloVe-style vectors are still just
   averaged per-word, which is a known-weak sentence representation
   compared to a model actually trained to produce sentence embeddings.
   Hugging Face (where most open sentence-transformer weights live)
   isn't reachable from this development sandbox, and no OpenAI/Cohere
   API key or running Ollama instance was available to test the
   already-built providers for those.
2. **An observation/fact-extraction preprocessing step.** LoCoMo's own
   paper (and, almost certainly, the systems scoring ~94%) don't
   retrieve over raw dialogue turns -- they first extract standalone
   facts/observations from the conversation, then retrieve over those.
   Raw turns like "I went to a LGBTQ support group yesterday" require
   the retriever to bridge "yesterday" to an absolute date and infer
   context a fact-extraction step would make explicit. Building that
   step well typically requires an LLM call per conversation, which
   wasn't available here either.

Both of these are real, identified, actionable next steps -- not vague
hand-waving -- they're just outside what this specific sandboxed session
could test. If you run this with real API access (an OpenAI key, or a
machine that can reach Hugging Face), re-running with a real embedding
provider is the highest-leverage next experiment, by a wide margin over
any further heuristic tuning of the current approach.

## What's next (concrete, not aspirational)

- ~~Add `--provider ollama` / `--model en_core_web_lg` CLI flags~~ (done);
  `--provider openai` / `--provider cohere` still to add
- Implement a simple observation-extraction preprocessing step and
  measure it in isolation from the embedding-quality lever, to see how
  much each contributes independently
- If claiming an end-to-end comparison against Mem0/Zep specifically,
  add an LLM-judge answering stage and report F1, not retrieval coverage

## What this evaluates — and what it doesn't (read before citing this)

- **Retrieval coverage, not end-to-end QA.** This checks whether
  `engine.retrieve()` surfaces the annotated evidence dialogue turn(s)
  in the top-k. It does not generate an answer or judge it — ContextFlow
  has no LLM-judge pipeline (`evaluation/faithfulness.py` is a
  documented stub). This is **not comparable** to F1/accuracy numbers
  reported by systems with an answer-generation stage (which is most
  published LoCoMo results, including Mem0's and Zep's).
- **Categories 3 (commonsense) and 5 (adversarial) are excluded**, not
  silently dropped — 542 of 1,986 questions. Category 3 is largely
  open-ended reasoning with no cited evidence turn; category 5 is
  adversarial (the premise is false). Neither is a meaningful target
  for "did retrieval find the right turn."
- **Raw dialogue turns only.** LoCoMo's own paper evaluates RAG systems
  against three different corpora: raw dialogs, generated
  "observations," and session summaries — and reports these perform
  differently. This only tests against raw dialogs, the simplest and
  likely hardest of the three for a system without a summarization
  step.
- **One run, this session's hardware/environment.** No repeated trials,
  no variance reported.

## Data license — read before you redistribute anything

LoCoMo is released under **CC BY-NC 4.0 (non-commercial)**. The
evaluation script downloads it at runtime rather than bundling it in
this repository, specifically so ContextFlow's Apache 2.0 license never
has to touch LoCoMo's non-commercial terms. Do not commit the
downloaded `locomo10.json` to this repository, and don't redistribute
it as part of any ContextFlow release or commercial offering — evaluating
against it locally, as this script does, is the intended and standard
use.

## Contributing

If you run this with a real embedding provider configured, please open
a PR updating this file with the real numbers and your configuration —
that's exactly the kind of contribution that would make this comparison
actually useful instead of admittedly incomplete.
