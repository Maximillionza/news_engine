"""
Local, contextual sentiment scoring via FinBERT (ProsusAI/finbert) —
the first-tier upgrade over the naive keyword lexicon in sentiment.py.

Why this exists: the lexicon can only ever match phrases it already knows,
verbatim. It has no way to handle hedged/conditional language ("rate hike
risk IF data surprises to upside" scored as a declarative "rate hike"),
and it has no way to score an article that expresses a clearly hawkish or
dovish read using words that simply aren't in the fixed phrase list. A
real language model reads the whole sentence, not a bag of phrases — it
generalizes past both problems, at the cost of not being free and not
being instant.

Honest limitation, not swept under the rug: FinBERT was trained on
general financial-news sentiment (positive/negative/neutral about a
security or company), not specifically on "is this hawkish or dovish for
the Fed." Mapping its positive/negative axis onto our USD-directional
axis (positive framing -> hawkish/USD-bullish, negative -> dovish/USD-
bearish) is a real simplification — see CONTEXTUAL_CONFIDENCE_THRESHOLD's
comment in config.settings for the fallback this triggers when FinBERT
itself isn't confident.

Gracefully unavailable if `torch`/`transformers` aren't installed (see
requirements-contextual.txt) — callers must check `is_available()` first
and fall back to a cheaper tier rather than crash. This keeps the base
install (`requirements.txt`) free of ~1GB+ of ML dependencies; FinBERT is
strictly opt-in.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from config.settings import FINBERT_MODEL_NAME

try:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    _DEPS_AVAILABLE = True
except ImportError:
    _DEPS_AVAILABLE = False


@dataclass
class FinBertResult:
    label: str          # "positive" | "negative" | "neutral"
    confidence: float    # 0.0-1.0, the winning label's probability
    usd_score: float      # -1.0 to +1.0, mapped onto the USD-directional axis


_model = None
_tokenizer = None
_load_failed = False


def is_available() -> bool:
    """
    True if the dependencies are installed AND the model has loaded (or
    can load) successfully. Callers should check this before scoring —
    it's the signal to fall back to the LLM tier or the lexicon instead.
    """
    if not _DEPS_AVAILABLE or _load_failed:
        return False
    return _ensure_loaded()


def _ensure_loaded() -> bool:
    """Lazy singleton load — the model only loads on first real use, not on import."""
    global _model, _tokenizer, _load_failed
    if _model is not None:
        return True
    if _load_failed:
        return False
    try:
        _tokenizer = AutoTokenizer.from_pretrained(FINBERT_MODEL_NAME)
        _model = AutoModelForSequenceClassification.from_pretrained(FINBERT_MODEL_NAME)
        _model.eval()
        return True
    except Exception as exc:  # noqa: BLE001 — any load failure should degrade gracefully, not crash scoring
        print(f"[finbert_sentiment] WARNING: failed to load {FINBERT_MODEL_NAME}: {exc}")
        _load_failed = True
        return False


def score_article_finbert(title: str, summary: str) -> Optional[FinBertResult]:
    """
    Returns None if the model isn't available — callers must handle that
    as "try the next tier," never as "score is neutral" (a real
    unavailable-model and a real neutral-content read are different
    things, same principle as EconomicEvent.usd_surprise_score()).
    """
    if not is_available():
        return None

    text = f"{title}. {summary}".strip()
    if not text or text == ".":
        return None

    with torch.no_grad():
        inputs = _tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        logits = _model(**inputs).logits
        probs = torch.nn.functional.softmax(logits, dim=-1)[0]

    # ProsusAI/finbert's label order per its config: positive, negative, neutral.
    id2label = _model.config.id2label
    scores = {id2label[i].lower(): probs[i].item() for i in range(len(probs))}

    top_label = max(scores, key=scores.get)
    top_confidence = scores[top_label]

    if top_label == "positive":
        usd_score = top_confidence
    elif top_label == "negative":
        usd_score = -top_confidence
    else:
        usd_score = 0.0

    return FinBertResult(label=top_label, confidence=top_confidence, usd_score=usd_score)
