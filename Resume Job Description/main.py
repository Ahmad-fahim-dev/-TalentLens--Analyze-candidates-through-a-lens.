"""
TalentLens — Candidate Analysis API (Bauhaus Edition)
=====================================================
FastAPI backend that serves `index.html` and exposes a matching engine
built on TF-IDF cosine similarity + skill-overlap scoring, implemented in
pure Python (no scikit-learn required) over `job_dataset.csv`.

TalentLens analyzes candidates through a "lens": every resume is refracted
against the full job corpus and scored with transparent, geometric math.

Run:  uvicorn main:app --reload
"""

import csv
import io
import math
import re
import zipfile
from collections import Counter
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "job_dataset.csv"

app = FastAPI(title="TalentLens API", version="1.1.0")

# --------------------------------------------------------------------------
# Data loading
# --------------------------------------------------------------------------

JOBS: list[dict] = []


def load_jobs() -> None:
    """Parse job_dataset.csv into structured records."""
    with DATASET_PATH.open(newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            JOBS.append(
                {
                    "job_id": row["JobID"].strip(),
                    "title": row["Title"].strip(),
                    "level": row["ExperienceLevel"].strip(),
                    "years": row["YearsOfExperience"].strip(),
                    "skills": [s.strip() for s in row["Skills"].split(";") if s.strip()],
                    "responsibilities": [
                        r.strip() for r in row["Responsibilities"].split(";") if r.strip()
                    ],
                    "keywords": [k.strip() for k in row["Keywords"].split(";") if k.strip()],
                }
            )


load_jobs()

# --------------------------------------------------------------------------
# Lightweight pure-Python TF-IDF engine
# --------------------------------------------------------------------------

STOPWORDS = frozenset(
    """
    a an the and or but if then than that this these those with without within
    to of in on for by at from as is are was were be been being it its it's
    will would should could can may might must do does did done have has had
    not no nor so such own same too very just also into over under again
    you your yours we our ours they them their he she his her i me my
    work works working use used using help helps helping support supporting
    apply applying learn learning follow following participate participating
    """.split()
)

TOKEN_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9\+\.\#]{1,}")
VECTORS: list[dict[str, float]] = []
IDF: dict[str, float] = {}


def tokenize(text: str) -> list[str]:
    lowered = text.lower()
    return [t for t in TOKEN_RE.findall(lowered) if t not in STOPWORDS and len(t) > 1]


def vectorize(tokens: list[str]) -> dict[str, float]:
    """TF-IDF vector (L2-normalised) from a token list."""
    tf = Counter(tokens)
    vec = {
        term: (1.0 + math.log(count)) * IDF.get(term, 0.0)
        for term, count in tf.items()
        if term in IDF
    }
    norm = math.sqrt(sum(w * w for w in vec.values())) or 1.0
    return {term: weight / norm for term, weight in vec.items()}


def build_index() -> None:
    """Pre-compute IDF + TF-IDF vectors for every job posting."""
    docs = []
    for job in JOBS:
        text = " ".join(
            [job["title"], job["level"], *job["skills"], *job["responsibilities"], *job["keywords"]]
        )
        docs.append(tokenize(text))

    n_docs = len(docs)
    df: Counter = Counter()
    for tokens in docs:
        df.update(set(tokens))

    global IDF
    IDF = {term: math.log((n_docs + 1) / (count + 1)) + 1.0 for term, count in df.items()}

    VECTORS.clear()
    VECTORS.extend(vectorize(tokens) for tokens in docs)


build_index()


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(w * b.get(term, 0.0) for term, w in a.items())


# --------------------------------------------------------------------------
# Skill matching
# --------------------------------------------------------------------------


def skill_present(resume_lower: str, skill: str) -> bool:
    """Case-insensitive word-ish boundary check for a skill string."""
    pattern = r"(?<![a-z0-9])" + re.escape(skill.lower()) + r"(?![a-z0-9])"
    return re.search(pattern, resume_lower) is not None


def score_job(index: int, resume_vec: dict[str, float], resume_lower: str) -> dict:
    job = JOBS[index]
    job_skills = list(dict.fromkeys(job["keywords"] + job["skills"]))
    matched = [s for s in job_skills if skill_present(resume_lower, s)]
    missing = [s for s in job_skills if s not in matched]

    tfidf_pct = cosine(resume_vec, VECTORS[index]) * 100.0
    skill_pct = (len(matched) / len(job_skills) * 100.0) if job_skills else 0.0
    match_pct = 0.5 * tfidf_pct + 0.5 * skill_pct

    return {
        "job_id": job["job_id"],
        "title": job["title"],
        "level": job["level"],
        "years": job["years"],
        "tfidf_pct": round(tfidf_pct, 1),
        "skill_pct": round(skill_pct, 1),
        "match_pct": round(match_pct, 1),
        "matched_skills": matched,
        "missing_skills": missing,
    }


# --------------------------------------------------------------------------
# .docx / .txt text extraction (dependency-free)
# --------------------------------------------------------------------------


def extract_text(filename: str, data: bytes) -> str:
    lower = (filename or "").lower()
    if lower.endswith(".docx"):
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            xml = zf.read("word/document.xml").decode("utf-8", errors="ignore")
        return " ".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", xml))
    if lower.endswith((".txt", ".md", ".text")) or not lower:
        return data.decode("utf-8", errors="ignore")
    raise HTTPException(status_code=415, detail="Unsupported file type. Upload .txt or .docx")


# --------------------------------------------------------------------------
# API routes
# --------------------------------------------------------------------------


class MatchRequest(BaseModel):
    text: str
    top_n: int = 8


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(BASE_DIR / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "jobs_indexed": len(JOBS)}


@app.get("/api/stats")
def stats() -> dict:
    levels = Counter(job["level"] for job in JOBS)
    return {
        "total_jobs": len(JOBS),
        "unique_titles": len({job["title"] for job in JOBS}),
        "levels": dict(levels),
        "unique_skills": len({s.lower() for job in JOBS for s in job["skills"]}),
    }


@app.get("/api/jobs")
def jobs() -> list[dict]:
    return [
        {
            "job_id": job["job_id"],
            "title": job["title"],
            "level": job["level"],
            "years": job["years"],
        }
        for job in JOBS
    ]


@app.post("/api/match")
def match(payload: MatchRequest) -> dict:
    text = payload.text.strip()
    if len(text) < 40:
        raise HTTPException(status_code=400, detail="Resume text is too short to analyse.")
    resume_vec = vectorize(tokenize(text))
    resume_lower = text.lower()
    results = [score_job(i, resume_vec, resume_lower) for i in range(len(JOBS))]
    results.sort(key=lambda r: r["match_pct"], reverse=True)
    top = results[: max(1, min(payload.top_n, 25))]
    return {
        "analyzed_chars": len(text),
        "results": top,
        "avg_top_match": round(sum(r["match_pct"] for r in top) / len(top), 1),
        "best_match": top[0]["match_pct"],
    }


@app.post("/api/match/file")
async def match_file(file: UploadFile = File(...), top_n: int = 8) -> dict:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file.")
    text = extract_text(file.filename or "", data)
    if len(text.strip()) < 40:
        raise HTTPException(status_code=400, detail="Could not extract enough text from the file.")
    return match(MatchRequest(text=text, top_n=top_n))

