# BlackBox Arena

A high-fidelity web application for CodeDecode-style black-box coding practice, featuring a daily puzzle (POTD) and an endless 300+ practice library.

## Core Premise
Each chamber seals a hidden mathematical or algorithmic transformation $f(\text{input}) \rightarrow \text{output}$.
Contenders cannot inspect the governing code. You may only stimulate the chamber with probe queries (up to 30 per chamber), analyze the responses, and submit Python code that faithfully reproduces $f(x)$ across 200 hidden edge cases.

---

## Visual Architecture: "The Monolith"
- **Matte Black Cube (Three.js)**: The central sculptural object, rendered with soft key and cool rim specular catchlights, contact occlusion shadow, and an easing cursor tilt (idle Lissajous drift on touch; respects `prefers-reduced-motion`).
- **Dynamic Front Canvas Texture**: Outputs appear embossed on the front face in monospace typography, accompanied by soft ripple wave pulses on transmission.
- **Severed Monolith Animation**: Upon conquering or surrendering a chamber, the cube splits along a 38° diagonal plane, exposing the inner geometric void and revealing the governing equation in colossal type.
- **Solid Field Chroma**: Full-bleed solid backgrounds per tier without gradients:
  - Easy: `#CFE0F2` (Ice Blue)
  - Medium: `#FF5A1F` (Tangerine)
  - Hard: `#4A0F1C` (Oxblood)
- **Hash-Routed Monograph Screens**:
  - `#today`: Daily Puzzle (POTD) with giant date numeral passing behind the cube and midnight IST countdown.
  - `#probe/<id>`: Oracle chamber with left Chronicle Tape, center 3D Monolith, and right architectural white Solver Plinth.
  - `#library`: 300 pre-generated chambers with 3D runway, tier filters, and full archival ledger table.
  - `#solved/<id>`: Severed Monolith state with declassified mathematical proof and query efficiency telemetry.
  - `#me`: Contender ledger tracking daily streaks in IST, solved totals by tier, and daily leaderboards.

---

## Secrecy Guarantees
- **Zero Client Leakage**: All 40+ composable primitives, parameter sets, and rule definitions live server-side only. Neither the API, nor errors, comments, nor test outputs leak rule data.
- **Cryptographic Seeding**: A random 256-bit `SERVER_SECRET` is generated on first boot and saved in a gitignored `.env`. Every seed is derived via `HMAC(SERVER_SECRET, label)`.
- **IST Daily Protocol**: One puzzle per day seeded from `HMAC(SERVER_SECRET, date in Asia/Kolkata)`. Weekly progression: Mon/Tue Easy, Wed/Thu/Fri Medium, Sat/Sun Hard.
- **Single Discrepancy Reporting**: On judge failure, the system isolates only ONE failing test case and its expected output. The underlying rule remains locked until solved or surrendered.

---

## Local Sandbox & Security Note
> [!IMPORTANT]
> The included Python execution sandbox executes user code in an isolated subprocess with a 2.0-second timeout, restricted builtins, and disabled filesystem and network sockets. This sandbox is designed for **local or personal practice**. For public multi-tenant production deployments, execute each submission inside an ephemeral sandboxed container (e.g. Docker / gVisor / Firecracker) with cgroup memory and CPU limits.

---

## Getting Started

### 1. Requirements
- Python 3.10+
- Modern Web Browser (Chrome, Edge, Firefox, Safari)

### 2. Installation
```bash
pip install -r requirements.txt
```

### 3. Running the Server
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Open your browser and navigate to:
`http://127.0.0.1:8000/#today`

### 4. Running the Test Suite
The test suite validates seed determinism, non-degeneracy, weekly tier patterns, sandbox isolation, judge correctness, and strict rule secrecy:
```bash
python -m pytest -q
```
*(Tests output pass/fail only, preserving contestant secrecy).*
