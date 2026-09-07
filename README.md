# TalentLens 🔭

**Analyze candidates through a lens.**

TalentLens is a resume-to-job matching engine wrapped in a bold **Bauhaus** interface.
Paste a resume (or upload `.txt` / `.docx`) and TalentLens refracts it through the lens of
**1,068 real job postings**, scoring every candidate with transparent, geometric math —
no black boxes, no AI hand-waving.

> **Form follows function.** Every element on the page is deliberately composed from
> circles, squares, and triangles in the pure Bauhaus primaries.

---

## ✨ Features

- **Paste or upload** — plain text (`/ .txt` / `.md`) or Word documents (`.docx`, parsed on
  the server with zero external dependencies)
- **Dual scoring engine** — `50% TF-IDF cosine similarity + 50% skill overlap`
- **Matched & missing skills** — see what to highlight and what to learn next
- **Live dataset stats** — jobs indexed, unique roles, unique skills, average match
- **Fully interactive UI** — accordion FAQ, animated score bars, mobile hamburger menu,
  physical "button press" micro-interactions
- **Zero-ML-dependency backend** — the TF-IDF engine is pure Python (no scikit-learn)

---

## 🧱 Tech Stack

| Layer      | Technology                                             |
| ---------- | ------------------------------------------------------ |
| Frontend   | Single-file `index.html` — Tailwind CSS (CDN), Outfit font (Google Fonts), Lucide icons |
| Backend    | FastAPI + Uvicorn (Python 3.10+)                       |
| Data       | `job_dataset.csv` — 1,068 job postings across levels    |
| Matching   | Pure-Python TF-IDF + skill-overlap scoring              |

---

## 🚀 Getting Started

### 1. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 2. Run the server

```powershell
python -m uvicorn main:app --reload
```

### 3. Open the app

- **Web app:** <http://127.0.0.1:8000>
- **Interactive API docs (Swagger):** <http://127.0.0.1:8000/docs>

---

## 🔌 API Reference

| Method   | Endpoint           | Description                                                        |
| -------- | ------------------ | ------------------------------------------------------------------ |
| `GET`    | `/`                | Serves the TalentLens web app                                       |
| `GET`    | `/api/health`      | Health check + number of jobs indexed                               |
| `GET`    | `/api/stats`       | Dataset statistics (jobs, roles, skills, experience levels)         |
| `GET`    | `/api/jobs`        | Full job catalog (id, title, level, years)                          |
| `POST`   | `/api/match`       | Match pasted resume text — JSON body `{ "text": "...", "top_n": 8 }` |
| `POST`   | `/api/match/file`  | Match an uploaded `.txt` / `.docx` file (multipart form, `file` field) |

### Example

```bash
curl -X POST http://127.0.0.1:8000/api/match -H "Content-Type: application/json" -d "{\"text\": \"Engineer skilled in C#, ASP.NET, SQL Server...\", \"top_n\": 3}"
```

```json
{
  "analyzed_chars": 276,
  "results": [
    {
      "job_id": "NET-F-004",
      "title": ".NET Developer",
      "level": "Fresher",
      "tfidf_pct": 66.4,
      "skill_pct": 90.9,
      "match_pct": 78.7,
      "matched_skills": [".NET", "C#", "SQL Server", "Entity Framework"],
      "missing_skills": ["ASP.NET basics"]
    }
  ],
  "avg_top_match": 76.4,
  "best_match": 78.7
}
```

---

## 🧮 How Matching Works

1. **Input** — resume text is extracted (raw text or `.docx` XML on the server).
2. **Vectorize** — the text becomes a TF-IDF vector, compared against a pre-computed
   vector for every job posting (title + skills + responsibilities + keywords).
3. **Score** — `match_pct = 0.5 × TF-IDF cosine similarity + 0.5 × skill overlap`,
   where skill overlap is the fraction of the job's required skills found in the resume.
4. **Act** — results are ranked; every match lists matched skills (yellow chips) and
   missing skills (muted chips) to prioritise learning.

---

## 📁 Project Structure

```
├── index.html               # Bauhaus frontend (single file)
├── main.py                  # FastAPI backend + matching engine
├── job_dataset.csv          # 1,068 job postings (source data)
├── requirements.txt         # fastapi, uvicorn, python-multipart
├── Resume_Job_Matcher.ipynb # Original analysis notebook
└── resume_job_matches.csv   # Sample match output from the notebook
```

---

## 🎨 The Bauhaus Design System

The UI follows a strict constructivist-modernist language:

- **Colors** — pure primaries only: Red `#D02020`, Blue `#1040C0`, Yellow `#F0C020`,
  grounded by black `#121212` on an off-white `#F0F0F0` canvas
- **Typography** — *Outfit* (geometric sans); massive `font-black` uppercase headlines
  with tight tracking, `uppercase tracking-widest` labels
- **Geometry** — binary radii (`rounded-none` or `rounded-full`), thick 2px/4px black
  borders, hard offset shadows (`4px/8px`, never blurred)
- **Color blocking** — hero panel (blue), stats (yellow), process (red), footer (near-black)
- **Motion** — mechanical and snappy: `duration-200`/`ease-out`, button press
  (`active:translate` + `shadow-none`), card hover lift, chevron flips
- **Brand mark** — a geometric **lens** (concentric circles) flanked by a square and a
  triangle, echoing the three-shape Bauhaus identity

---

## 📝 Notes

- The frontend loads Tailwind, fonts, and icons from CDNs — internet is required on
  first load.
- The matching engine intentionally mirrors the approach from `Resume_Job_Matcher.ipynb`
  (TF-IDF + skill overlap) but is reimplemented dependency-free so the API runs anywhere
  Python runs.
