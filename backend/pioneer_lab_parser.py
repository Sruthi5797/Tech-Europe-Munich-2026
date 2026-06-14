"""
LiverLink — Pioneer Lab Image Parser

Two inference modes:
  gliner2 (default) — Step 1: OCR with Gemini Flash  →  Step 2: GLiNER2 structured
                      extraction via Pioneer's native /inference endpoint.
                      Smaller, faster, cheaper.
  claude             — Direct vision inference via Pioneer's Anthropic-compatible
                      endpoint with claude-sonnet-4-6.

Usage:
    python pioneer_lab_parser.py                          # all patients, gliner2
    python pioneer_lab_parser.py PT-2026-14902            # one patient, gliner2
    python pioneer_lab_parser.py PT-2026-14902 --model claude
    python pioneer_lab_parser.py --dry-run                # list without API calls

Environment:
    PIONEER_API_KEY  — required
    GOOGLE_API_KEY   — required for gliner2 OCR step
"""

import base64
import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------
TEST_DATA_DIR = Path(__file__).parent.parent / "data" / "test_data"
PIONEER_INFERENCE_URL = "https://api.pioneer.ai/inference"
PIONEER_MESSAGES_URL  = "https://api.pioneer.ai/v1/messages"
GLINER2_MODEL         = "fastino/gliner2-base-v1"
CLAUDE_MODEL          = "claude-sonnet-4-6"

# ---------------------------------------------------------------------------
# GLiNER2 structures schema for LFT lab reports
# ---------------------------------------------------------------------------
LFT_STRUCTURES_SCHEMA = {
    "structures": {
        "lab_report": {
            "fields": [
                {"name": "patient_id",          "dtype": "str",  "description": "Patient ID, case number, or lab accession number"},
                {"name": "patient_name",         "dtype": "str",  "description": "Full name of the patient"},
                {"name": "date_of_birth",        "dtype": "str",  "description": "Patient date of birth"},
                {"name": "age",                  "dtype": "str",  "description": "Patient age in years"},
                {"name": "gender",               "dtype": "str",  "description": "Patient sex or gender", "choices": ["Male", "Female", "M", "F"]},
                {"name": "report_date",          "dtype": "str",  "description": "Date the lab report was issued or collected"},
                {"name": "referring_physician",  "dtype": "str",  "description": "Name of the referring or ordering doctor"},
                {"name": "lab_name",             "dtype": "str",  "description": "Name of the laboratory or hospital"},
                {"name": "ALT",                  "dtype": "str",  "description": "ALT (alanine aminotransferase) or SGPT result value with unit"},
                {"name": "AST",                  "dtype": "str",  "description": "AST (aspartate aminotransferase) or SGOT result value with unit"},
                {"name": "ALP",                  "dtype": "str",  "description": "ALP (alkaline phosphatase) result value with unit"},
                {"name": "total_bilirubin",      "dtype": "str",  "description": "Total bilirubin result value with unit"},
                {"name": "direct_bilirubin",     "dtype": "str",  "description": "Direct or conjugated bilirubin result value with unit"},
                {"name": "albumin",              "dtype": "str",  "description": "Albumin result value with unit"},
                {"name": "total_proteins",       "dtype": "str",  "description": "Total protein result value with unit"},
                {"name": "GGT",                  "dtype": "str",  "description": "GGT (gamma-glutamyl transferase) result value with unit"},
                {"name": "PT",                   "dtype": "str",  "description": "Prothrombin time result value with unit"},
                {"name": "INR",                  "dtype": "str",  "description": "INR (international normalised ratio) result value"},
                {"name": "ALT_ref_range",        "dtype": "str",  "description": "Reference range for ALT"},
                {"name": "AST_ref_range",        "dtype": "str",  "description": "Reference range for AST"},
                {"name": "ALP_ref_range",        "dtype": "str",  "description": "Reference range for ALP"},
                {"name": "total_bilirubin_ref",  "dtype": "str",  "description": "Reference range for total bilirubin"},
                {"name": "albumin_ref",          "dtype": "str",  "description": "Reference range for albumin"},
            ],
        }
    }
}

# ---------------------------------------------------------------------------
# Claude extraction prompt (vision mode)
# ---------------------------------------------------------------------------
CLAUDE_EXTRACTION_PROMPT = """You are a medical data extraction assistant. Extract all data from this liver function test (LFT) lab report image and return a single JSON object.

Return ONLY valid JSON — no markdown, no explanation, no code fences.

{
  "patient_id": "<patient ID from report>",
  "name": "<full patient name>",
  "dob": "<date of birth>",
  "age": <integer age>,
  "gender": "<Male or Female>",
  "report_date": "<report date>",
  "accession_number": "<accession number>",
  "referring_physician": "<physician name>",
  "lab_name": "<laboratory name>",
  "lab_address": "<lab address>",
  "biomarkers": {
    "ALT":             {"value": <number or null>, "unit": "<unit>", "reference_range": "<range>", "flag": "<H, L, or null>"},
    "AST":             {"value": <number or null>, "unit": "<unit>", "reference_range": "<range>", "flag": "<H, L, or null>"},
    "ALP":             {"value": <number or null>, "unit": "<unit>", "reference_range": "<range>", "flag": "<H, L, or null>"},
    "total_bilirubin": {"value": <number or null>, "unit": "<unit>", "reference_range": "<range>", "flag": "<H, L, or null>"},
    "direct_bilirubin":{"value": <number or null>, "unit": "<unit>", "reference_range": "<range>", "flag": "<H, L, or null>"},
    "albumin":         {"value": <number or null>, "unit": "<unit>", "reference_range": "<range>", "flag": "<H, L, or null>"},
    "total_proteins":  {"value": <number or null>, "unit": "<unit>", "reference_range": "<range>", "flag": "<H, L, or null>"},
    "GGT":             {"value": <number or null>, "unit": "<unit>", "reference_range": "<range>", "flag": "<H, L, or null>"},
    "PT":              {"value": <number or null>, "unit": "<unit>", "reference_range": "<range>", "flag": "<H, L, or null>"},
    "INR":             {"value": <number or null>, "unit": "<unit>", "reference_range": "<range>", "flag": "<H, L, or null>"}
  },
  "comments": "<clinical comments from the report, or null>"
}"""

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def encode_image(image_path: Path) -> str:
    return base64.standard_b64encode(image_path.read_bytes()).decode("utf-8")


def _strip_fences(text: str) -> str:
    cleaned = text.strip()
    for prefix in ("```json", "```"):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
    return cleaned.removesuffix("```").strip()


# ---------------------------------------------------------------------------
# Step 1 (GLiNER2 path): OCR with Gemini Flash
# ---------------------------------------------------------------------------
OCR_PROMPT = (
    "Transcribe every word, number, unit, and punctuation mark from this medical lab "
    "report image exactly as printed. Preserve the layout using spaces and newlines. "
    "Output plain text only — no commentary, no formatting changes."
)

def ocr_images_with_gemini(image_paths: list[Path], google_api_key: str) -> str:
    """Use Gemini Flash to OCR one or more lab report images into plain text."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=google_api_key)

    parts = []
    for img_path in image_paths:
        parts.append(
            types.Part.from_bytes(data=img_path.read_bytes(), mime_type="image/jpeg")
        )
    parts.append(types.Part.from_text(text=OCR_PROMPT))

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=parts,
    )
    return response.text


# ---------------------------------------------------------------------------
# Step 2 (GLiNER2 path): Pioneer native /inference with structures schema
# ---------------------------------------------------------------------------

def call_pioneer_gliner2(text: str, pioneer_api_key: str) -> dict:
    """Run GLiNER2 structured extraction on OCR text via Pioneer's /inference."""
    payload = {
        "model_id":  GLINER2_MODEL,
        "text":      text,
        "schema":    LFT_STRUCTURES_SCHEMA,
        "threshold": 0.3,   # lower threshold tolerates noisy OCR text
    }

    response = requests.post(
        PIONEER_INFERENCE_URL,
        headers={
            "X-API-Key":    pioneer_api_key,
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def gliner2_result_to_lft(raw: dict, patient_id: str) -> dict:
    """Normalise Pioneer GLiNER2 structures response into our LFT JSON shape."""
    # Pioneer returns: {"result": {"data" or "structures": {"lab_report": [{field: {"text": value}, ...}]}}}
    result_obj = raw.get("result", {})
    structures = result_obj.get("data", {})
    if not structures:
        structures = result_obj.get("structures", {})
    instances  = structures.get("lab_report", [{}])
    fields     = instances[0] if instances else {}

    def get_val(field_obj):
        if isinstance(field_obj, dict):
            return field_obj.get("text")
        return field_obj

    def num(val):
        val_text = get_val(val)
        if val_text is None:
            return None
        import re
        tokens = re.findall(r"[-+]?\d*\.?\d+", str(val_text).replace(",", ""))
        for token in tokens:
            if token in ("", ".", "-", "+", "-.", "+."):
                continue
            try:
                return float(token)
            except ValueError:
                continue
        return None

    return {
        "patient_id":          patient_id,
        "name":                get_val(fields.get("patient_name")),
        "dob":                 get_val(fields.get("date_of_birth")),
        "age":                 num(fields.get("age")),
        "gender":              get_val(fields.get("gender")),
        "report_date":         get_val(fields.get("report_date")),
        "referring_physician": get_val(fields.get("referring_physician")),
        "lab_name":            get_val(fields.get("lab_name")),
        "biomarkers": {
            "ALT":             num(fields.get("ALT")),
            "AST":             num(fields.get("AST")),
            "ALP":             num(fields.get("ALP")),
            "total_bilirubin": num(fields.get("total_bilirubin")),
            "direct_bilirubin":num(fields.get("direct_bilirubin")),
            "albumin":         num(fields.get("albumin")),
            "total_proteins":  num(fields.get("total_proteins")),
            "GGT":             num(fields.get("GGT")),
            "PT":              num(fields.get("PT")),
            "INR":             num(fields.get("INR")),
        },
        "reference_ranges": {
            "ALT":             get_val(fields.get("ALT_ref_range")),
            "AST":             get_val(fields.get("AST_ref_range")),
            "ALP":             get_val(fields.get("ALP_ref_range")),
            "total_bilirubin": get_val(fields.get("total_bilirubin_ref")),
            "albumin":         get_val(fields.get("albumin_ref")),
        },
        "_raw_gliner2": raw,   # keep full Pioneer response for debugging
    }


# ---------------------------------------------------------------------------
# Claude path (Anthropic-compatible endpoint, vision)
# ---------------------------------------------------------------------------

def call_pioneer_claude(image_paths: list[Path], pioneer_api_key: str) -> dict:
    """Send image(s) to Pioneer's Anthropic-compatible endpoint."""
    content = [
        {
            "type": "image",
            "source": {
                "type":       "base64",
                "media_type": "image/jpeg",
                "data":       encode_image(p),
            },
        }
        for p in image_paths
    ]
    content.append({"type": "text", "text": CLAUDE_EXTRACTION_PROMPT})

    response = requests.post(
        PIONEER_MESSAGES_URL,
        headers={"X-API-Key": pioneer_api_key, "Content-Type": "application/json"},
        json={
            "model":      CLAUDE_MODEL,
            "max_tokens": 2048,
            "messages":   [{"role": "user", "content": content}],
        },
        timeout=60,
    )
    response.raise_for_status()

    raw_text = "".join(
        b.get("text", "")
        for b in response.json().get("content", [])
        if b.get("type") == "text"
    )
    return json.loads(_strip_fences(raw_text))


# ---------------------------------------------------------------------------
# Gemini direct extraction (fallback when Pioneer billing not active)
# ---------------------------------------------------------------------------

GEMINI_EXTRACTION_PROMPT = """You are a medical data extraction assistant. Extract all data from this liver function test (LFT) lab report image and return a single JSON object.

Return ONLY valid JSON — no markdown, no explanation, no code fences.

{
  "patient_id": "<patient ID from report>",
  "name": "<full patient name>",
  "dob": "<date of birth>",
  "age": <integer age>,
  "gender": "<Male or Female>",
  "report_date": "<report date>",
  "accession_number": "<accession number>",
  "referring_physician": "<physician name>",
  "lab_name": "<laboratory name>",
  "lab_address": "<lab address>",
  "biomarkers": {
    "ALT":             {"value": <number or null>, "unit": "<unit>", "reference_range": "<range>", "flag": "<H, L, or null>"},
    "AST":             {"value": <number or null>, "unit": "<unit>", "reference_range": "<range>", "flag": "<H, L, or null>"},
    "ALP":             {"value": <number or null>, "unit": "<unit>", "reference_range": "<range>", "flag": "<H, L, or null>"},
    "total_bilirubin": {"value": <number or null>, "unit": "<unit>", "reference_range": "<range>", "flag": "<H, L, or null>"},
    "direct_bilirubin":{"value": <number or null>, "unit": "<unit>", "reference_range": "<range>", "flag": "<H, L, or null>"},
    "albumin":         {"value": <number or null>, "unit": "<unit>", "reference_range": "<range>", "flag": "<H, L, or null>"},
    "total_proteins":  {"value": <number or null>, "unit": "<unit>", "reference_range": "<range>", "flag": "<H, L, or null>"},
    "GGT":             {"value": <number or null>, "unit": "<unit>", "reference_range": "<range>", "flag": "<H, L, or null>"},
    "PT":              {"value": <number or null>, "unit": "<unit>", "reference_range": "<range>", "flag": "<H, L, or null>"},
    "INR":             {"value": <number or null>, "unit": "<unit>", "reference_range": "<range>", "flag": "<H, L, or null>"}
  },
  "comments": "<clinical comments from the report, or null>"
}"""


def extract_with_gemini(image_paths: list[Path], patient_id: str, google_api_key: str) -> dict:
    """Single-step extraction: image → structured JSON, entirely via Gemini."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=google_api_key)

    parts = [
        types.Part.from_bytes(data=p.read_bytes(), mime_type="image/jpeg")
        for p in image_paths
    ]
    parts.append(types.Part.from_text(text=GEMINI_EXTRACTION_PROMPT))

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=parts,
    )

    result = json.loads(_strip_fences(response.text))
    result["patient_id"] = patient_id
    return result


# ---------------------------------------------------------------------------
# Patient discovery
# ---------------------------------------------------------------------------

def find_patient_images(patient_dir: Path) -> list[Path]:
    """Return sorted list of JPG images in a patient directory."""
    return sorted(patient_dir.glob("*.jpg")) + sorted(patient_dir.glob("*.jpeg"))


def get_all_patients() -> list[Path]:
    """Return all patient directories in test_data/."""
    return sorted(p for p in TEST_DATA_DIR.iterdir() if p.is_dir())


# ---------------------------------------------------------------------------
# Processing
# ---------------------------------------------------------------------------

def process_patient(
    patient_dir: Path,
    pioneer_api_key: str,
    google_api_key: str,
    mode: str,
    force: bool = False,
) -> dict | None:
    patient_id = patient_dir.name
    images = find_patient_images(patient_dir)

    if not images:
        print(f"  [{patient_id}] No images found — skipping.")
        return None

    suffix = f"_{mode}"
    output_path = patient_dir / f"{patient_id}_parsed{suffix}.json"

    if output_path.exists() and not force:
        print(f"  [{patient_id}] Already parsed ({mode}) — loading existing result.")
        return json.loads(output_path.read_text(encoding="utf-8"))

    if mode == "gliner2":
        print(f"  [{patient_id}] Step 1/2 — OCR with Gemini Flash ({len(images)} image(s))...")
        ocr_text = ocr_images_with_gemini(images, google_api_key)
        print(f"  [{patient_id}] Step 2/2 — GLiNER2 extraction via Pioneer...")
        raw = call_pioneer_gliner2(ocr_text, pioneer_api_key)
        result = gliner2_result_to_lft(raw, patient_id)
        result["_ocr_text"] = ocr_text
    elif mode == "gemini":
        print(f"  [{patient_id}] Extracting with Gemini 2.5 Flash ({len(images)} image(s))...")
        result = extract_with_gemini(images, patient_id, google_api_key)
    else:
        print(f"  [{patient_id}] Sending {len(images)} image(s) to Pioneer (Claude)...")
        result = call_pioneer_claude(images, pioneer_api_key)
        result["patient_id"] = patient_id

    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  [{patient_id}] Saved → {output_path.relative_to(Path(__file__).parent.parent)}")
    return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _parse_args(args: list[str]) -> tuple[str, bool, bool, list[str]]:
    """Return (mode, dry_run, force, patient_ids)."""
    mode = "gliner2"
    dry_run = "--dry-run" in args
    force   = "--force"   in args

    # --model gliner2 | claude
    if "--model" in args:
        idx = args.index("--model")
        if idx + 1 < len(args):
            mode = args[idx + 1]

    target_ids = [
        a for a in args
        if not a.startswith("--") and a not in (mode,)
    ]
    return mode, dry_run, force, target_ids


def main() -> None:
    pioneer_api_key = os.getenv("PIONEER_API_KEY", "").strip()
    google_api_key  = os.getenv("GOOGLE_API_KEY",  "").strip()

    mode, dry_run, force, target_ids = _parse_args(sys.argv[1:])

    if not dry_run:
        if mode in ("gliner2", "claude") and not pioneer_api_key:
            print("ERROR: PIONEER_API_KEY is not set in .env")
            sys.exit(1)
        if mode in ("gliner2", "gemini") and not google_api_key:
            print("ERROR: GOOGLE_API_KEY is required for this mode")
            sys.exit(1)

    if target_ids:
        patient_dirs = [TEST_DATA_DIR / pid for pid in target_ids]
        for d in patient_dirs:
            if not d.is_dir():
                print(f"ERROR: Patient directory not found: {d}")
                sys.exit(1)
    else:
        patient_dirs = get_all_patients()

    model_label = f"GLiNER2 ({GLINER2_MODEL})" if mode == "gliner2" else f"Claude ({CLAUDE_MODEL})" if mode == "claude" else "Gemini (gemini-2.5-flash, full extraction)"
    print(f"Pioneer Lab Parser — {model_label}")
    print(f"Processing {len(patient_dirs)} patient(s) from {TEST_DATA_DIR}\n")

    if dry_run:
        for d in patient_dirs:
            imgs = find_patient_images(d)
            print(f"  {d.name}: {len(imgs)} image(s) — {[i.name for i in imgs]}")
        return

    results, errors = {}, []

    for patient_dir in patient_dirs:
        try:
            result = process_patient(patient_dir, pioneer_api_key, google_api_key, mode, force)
            if result:
                results[patient_dir.name] = result
        except requests.HTTPError as exc:
            msg = f"{patient_dir.name}: HTTP {exc.response.status_code} — {exc.response.text[:300]}"
            print(f"  ERROR {msg}")
            errors.append(msg)
        except json.JSONDecodeError as exc:
            msg = f"{patient_dir.name}: JSON parse error — {exc}"
            print(f"  ERROR {msg}")
            errors.append(msg)
        except Exception as exc:  # noqa: BLE001
            msg = f"{patient_dir.name}: {type(exc).__name__}: {exc}"
            print(f"  ERROR {msg}")
            errors.append(msg)

    print(f"\nDone. {len(results)} succeeded, {len(errors)} failed.")
    if errors:
        print("Errors:")
        for e in errors:
            print(f"  - {e}")


if __name__ == "__main__":
    main()
