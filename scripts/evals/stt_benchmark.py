#!/usr/bin/env python3
"""
STT benchmark on interview-style answers: Polly voices (Indian + US English) with laptop-like noise, scored by
word error rate and technical-term accuracy, for whisper base.en vs Amazon Transcribe (en-IN, with/without vocabulary).

    backend/venv/bin/python scripts/evals/stt_benchmark.py
Synthetic speech is still kinder than a real mic; treat absolute numbers as optimistic, the ranking as the signal.
"""
import asyncio
import io
import json
import re
import sys
import time
import wave
from datetime import datetime
from pathlib import Path

import boto3
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

SENTENCES = [
    ("I would put Redis in front of PostgreSQL and invalidate the cache when the row changes.", ["redis", "postgresql"]),
    ("The lookup is O of one because I store the complement in a hashmap.", ["hashmap"]),
    ("To make the payment endpoint idempotent, the client sends an idempotency key with every request.", ["idempotent", "idempotency"]),
    ("I used memoization on top of the recursion, so the dynamic programming solution runs in O of n squared.", ["memoization", "dynamic", "programming"]),
    ("For the course schedule problem I did a topological sort with Kahn's algorithm and a queue.", ["topological", "kahn's"]),
    ("We moved the events to Kafka so the consumers can apply backpressure when they fall behind.", ["kafka", "backpressure"]),
    ("A trie lets you match prefixes in time proportional to the length of the word.", ["trie"]),
    ("The rate limiter uses a token bucket per user, stored in Redis with a TTL.", ["token", "bucket", "redis"]),
    ("I deployed it on Kubernetes behind an Nginx load balancer with three replicas.", ["kubernetes", "nginx"]),
    ("Two threads were taking the locks in a different order, which caused a deadlock under load.", ["deadlock"]),
    ("I'd shard the table by user ID and use consistent hashing so adding a node moves few keys.", ["shard", "consistent", "hashing"]),
    ("The FastAPI service validates the JWT, then calls the gRPC backend asynchronously.", ["fastapi", "jwt", "grpc"]),
]
VOICES = [("Kajal", "generative", "en-IN"), ("Aditi", "standard", "hi-IN"), ("Matthew", "generative", "en-US")]


def norm(t: str) -> list:
    t = t.lower().replace("o(1)", "o of one").replace("o(n^2)", "o of n squared")
    return re.findall(r"[a-z0-9']+", t)


def wer(ref: str, hyp: str) -> float:
    r, h = norm(ref), norm(hyp)
    d = list(range(len(h) + 1))
    for i in range(1, len(r) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(h) + 1):
            cur = min(d[j] + 1, d[j - 1] + 1, prev + (r[i - 1] != h[j - 1]))
            prev, d[j] = d[j], cur
    return d[len(h)] / max(1, len(r))


def term_hits(terms, hyp: str) -> int:
    words = set(norm(hyp))
    joined = " ".join(norm(hyp))
    return sum(1 for t in terms if t in words or t.replace("'", "") in joined.replace("'", ""))


def synth(polly, text, voice, engine, lang) -> bytes:
    r = polly.synthesize_speech(Text=text, VoiceId=voice, Engine=engine, OutputFormat="pcm", SampleRate="16000",
                                LanguageCode=lang)
    pcm = np.frombuffer(r["AudioStream"].read(), dtype=np.int16).astype(np.float32)
    rng = np.random.default_rng(len(text))
    # Laptop-ish: fan hiss at ~22 dB SNR plus a little low hum, then back to 16-bit WAV.
    sig = np.sqrt(np.mean(pcm ** 2)) or 1.0
    noise = rng.normal(0, sig / (10 ** (22 / 20)), pcm.shape) + 0.02 * sig * np.sin(2 * np.pi * 120 * np.arange(len(pcm)) / 16000)
    out = np.clip(pcm + noise, -32768, 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(out.tobytes())
    return buf.getvalue()


async def main():
    from backend.app.audio import transcribe_aws
    from backend.app.audio.service import _get_whisper_model
    from backend.app.core.config import settings

    polly = boto3.client("polly", region_name="us-east-1")
    clips = []
    for voice, engine, lang in VOICES:
        for text, terms in SENTENCES:
            clips.append((voice, text, terms, synth(polly, text, voice, engine, lang)))
    print(f"{len(clips)} clips synthesized", flush=True)

    whisper = _get_whisper_model()
    prompt = ("Technical engineering interview: LeetCode, DSA, Big-O notation, O(1), dynamic programming, memoization, "
              "Redis, Kafka, PostgreSQL, Kubernetes, idempotency, hashmap, trie, gRPC, JWT, FastAPI.")

    def run_whisper(wav: bytes) -> str:
        segs, _ = whisper.transcribe(io.BytesIO(wav), language="en", beam_size=5, vad_filter=True, initial_prompt=prompt)
        return " ".join(s.text for s in segs)

    async def run_transcribe(wav: bytes, vocab: str) -> str:
        settings.TRANSCRIBE_VOCABULARY = vocab
        pcm = await asyncio.to_thread(transcribe_aws.decode_to_pcm16k, wav)
        return await transcribe_aws.transcribe_pcm(pcm)

    engines = {
        "whisper base.en": lambda w: asyncio.to_thread(run_whisper, w),
        "transcribe en-IN": lambda w: run_transcribe(w, ""),
        "transcribe en-IN + vocab": lambda w: run_transcribe(w, "skillissue-tech-en-IN"),
    }
    rows = {k: [] for k in engines}
    for voice, text, terms, wav in clips:
        for name, fn in engines.items():
            t0 = time.perf_counter()
            try:
                hyp = await fn(wav)
            except Exception as e:
                hyp = f"<error {type(e).__name__}>"
            rows[name].append({"voice": voice, "ref": text, "hyp": hyp, "wer": wer(text, hyp),
                               "terms": len(terms), "hits": term_hits(terms, hyp), "secs": time.perf_counter() - t0})
    summary = {}
    for name, rs in rows.items():
        summary[name] = {
            "wer": round(sum(r["wer"] for r in rs) / len(rs), 3),
            "term_accuracy": round(sum(r["hits"] for r in rs) / sum(r["terms"] for r in rs), 3),
            "p50_secs": round(sorted(r["secs"] for r in rs)[len(rs) // 2], 2),
            "by_voice_wer": {v: round(np.mean([r["wer"] for r in rs if r["voice"] == v]), 3) for v, _, _ in VOICES},
        }
    print(json.dumps(summary, indent=1))
    worst = sorted(rows["whisper base.en"], key=lambda r: -r["wer"])[:4]
    print("\nwhisper worst:", *[f"[{r['voice']}] {r['hyp']!r}" for r in worst], sep="\n  ")
    worst = sorted(rows["transcribe en-IN + vocab"], key=lambda r: -r["wer"])[:4]
    print("transcribe+vocab worst:", *[f"[{r['voice']}] {r['hyp']!r}" for r in worst], sep="\n  ")
    out = ROOT / "artifacts_e2e" / "evals" / f"stt-{datetime.now():%Y%m%d-%H%M%S}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"summary": summary, "rows": rows}, indent=1))
    print("saved", out)


if __name__ == "__main__":
    asyncio.run(main())
