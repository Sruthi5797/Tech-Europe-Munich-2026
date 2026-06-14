"""
Tool functions for the LiverLink Hepatology Doctor Agent.

Provides clinical calculators (MELD-Na, Child-Pugh), evidence-based pathway
lookups, and web search for up-to-date medical guidelines.
"""

import math
import os

from tavily import TavilyClient


def search_web(query: str) -> dict:
    """Searches the web for information using the Tavily Search API.
    Use this tool whenever the user asks general knowledge questions,
    recent events, or queries that require real-time or external web data.

    Args:
        query (str): The search query to send to Tavily.

    Returns:
        dict: A dictionary with the search status and results or an error message.
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return {
            "status": "error",
            "error_message": (
                "TAVILY_API_KEY environment variable is not set. "
                "Please configure the TAVILY_API_KEY."
            ),
        }
    try:
        client = TavilyClient(api_key=api_key)
        response = client.search(query=query)
        return {
            "status": "success",
            "results": response.get("results", []),
            "answer": response.get("answer", None),
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Failed to perform search: {str(e)}",
        }


def calculate_meld_na(
    bilirubin: float, creatinine: float, inr: float, sodium: float
) -> dict:
    """Calculates the MELD-Na (Model for End-Stage Liver Disease) score for
    liver transplant prioritization. Standard OPTN/UNOS 2016 policy formula.

    Args:
        bilirubin (float): Serum total bilirubin (mg/dL).
        creatinine (float): Serum creatinine (mg/dL). Capped at 4.0 mg/dL.
        inr (float): International Normalized Ratio.
        sodium (float): Serum sodium (mEq/L). Capped between 125 and 137 mEq/L.

    Returns:
        dict: Computed MELD-Na score, intermediate MELD(i), and interpretation.
    """
    try:
        cr_val = min(max(creatinine, 1.0), 4.0)
        bili_val = max(bilirubin, 1.0)
        inr_val = max(inr, 1.0)
        na_val = min(max(sodium, 125.0), 137.0)

        meld_i = (
            0.957 * math.log(cr_val)
            + 0.378 * math.log(bili_val)
            + 1.120 * math.log(inr_val)
            + 0.643
        )
        meld_i = round(meld_i * 10, 4)

        meld_na_score = meld_i
        if meld_i > 11.0:
            meld_na_score = meld_i + 1.32 * (137.0 - na_val) - (
                0.025 * meld_i * (137.0 - na_val)
            )

        final_score = int(round(meld_na_score))

        mortality_map = {
            "<=9": "1.9% estimated 3-month mortality",
            "10-19": "6.0% estimated 3-month mortality",
            "20-29": "19.6% estimated 3-month mortality",
            "30-39": "52.6% estimated 3-month mortality",
            ">=40": "71.3% estimated 3-month mortality",
        }

        if final_score <= 9:
            mort = mortality_map["<=9"]
        elif final_score <= 19:
            mort = mortality_map["10-19"]
        elif final_score <= 29:
            mort = mortality_map["20-29"]
        elif final_score <= 39:
            mort = mortality_map["30-39"]
        else:
            mort = mortality_map[">=40"]

        return {
            "status": "success",
            "meld_i": round(meld_i, 1),
            "meld_na": final_score,
            "estimated_3mo_mortality": mort,
            "clinical_recommendation": (
                "Refer for Liver Transplant evaluation if MELD-Na >= 15. "
                "For scores >= 25, consider immediate ICU/tertiary center consult."
            ),
        }
    except Exception as e:
        return {"status": "error", "error_message": f"Calculation error: {str(e)}"}


def calculate_child_pugh(
    bilirubin: float,
    albumin: float,
    inr: float,
    ascites: str,
    encephalopathy: str,
) -> dict:
    """Calculates the Child-Pugh Score and Class to assess severity of
    cirrhosis and liver disease prognosis.

    Args:
        bilirubin (float): Serum total bilirubin (mg/dL).
        albumin (float): Serum albumin (g/dL).
        inr (float): International Normalized Ratio.
        ascites (str): Presence of ascites. Options: 'None', 'Mild'
            (diuretic-responsive), 'Moderate-Severe' (diuretic-refractory).
        encephalopathy (str): Presence of hepatic encephalopathy. Options:
            'None', 'Grade I-II' (mild), 'Grade III-IV' (severe).

    Returns:
        dict: Child-Pugh points, Class (A, B, or C), and prognosis details.
    """
    try:
        points = 0

        if bilirubin < 2.0:
            points += 1
        elif bilirubin <= 3.0:
            points += 2
        else:
            points += 3

        if albumin > 3.5:
            points += 1
        elif albumin >= 2.8:
            points += 2
        else:
            points += 3

        if inr < 1.7:
            points += 1
        elif inr <= 2.3:
            points += 2
        else:
            points += 3

        asc = ascites.lower()
        if "none" in asc:
            points += 1
        elif "mild" in asc:
            points += 2
        else:
            points += 3

        he = encephalopathy.lower()
        if "none" in he:
            points += 1
        elif "i-ii" in he or "mild" in he:
            points += 2
        else:
            points += 3

        if points <= 6:
            pugh_class = "A"
            survival = "1-year survival: 100%, 2-year survival: 85%"
            stage = "Well-compensated liver disease."
        elif points <= 9:
            pugh_class = "B"
            survival = "1-year survival: 80%, 2-year survival: 60%"
            stage = "Significant functional compromise. Consider transplant referral."
        else:
            pugh_class = "C"
            survival = "1-year survival: 45%, 2-year survival: 35%"
            stage = "Decompensated liver disease. High priority transplant candidacy."

        return {
            "status": "success",
            "total_points": points,
            "class": pugh_class,
            "prognosis_survival": survival,
            "functional_stage": stage,
        }
    except Exception as e:
        return {"status": "error", "error_message": f"Calculation error: {str(e)}"}


def get_hepatology_clinical_pathway(condition: str) -> dict:
    """Returns official clinical pathways, criteria, and guidelines
    (e.g. AASLD, EASL) for specific liver conditions.

    Args:
        condition (str): The liver condition or guideline query
            (e.g., 'HCC Surveillance', 'MASH/NAFLD', 'Ascites',
            'Encephalopathy', 'Varices').

    Returns:
        dict: Standard guidelines, diagnostic criteria, and clinical pathways.
    """
    cond = condition.lower()

    pathways = {
        "hcc": {
            "guideline": "AASLD 2018 / EASL 2018 Hepatocellular Carcinoma Guidelines",
            "eligibility": (
                "All patients with cirrhosis (any etiology) or patients with "
                "chronic Hepatitis B (even without cirrhosis if high risk)."
            ),
            "modality": (
                "Abdominal Ultrasound combined with Serum Alpha-Fetoprotein (AFP) "
                "every 6 months."
            ),
            "diagnostic_cutoff": (
                "Lesions < 1cm: repeat ultrasound in 3-4 months. Lesions >= 1cm: "
                "dynamic contrast-enhanced CT or multiphasic MRI indicating arterial "
                "hyperenhancement and venous/delayed phase washout (LI-RADS staging)."
            ),
        },
        "mash": {
            "alias": "MASH / Metabolic Dysfunction-Associated Steatohepatitis (formerly NASH)",
            "guideline": "AASLD / AGA Clinical Practice Update on MASH Staging & Management",
            "risk_stratification": (
                "FIB-4 score = (Age x AST) / (Platelet Count x sqrt(ALT)). "
                "FIB-4 < 1.3: low risk; FIB-4 > 2.67: high risk (requires immediate "
                "FibroScan or magnetic resonance elastography)."
            ),
            "therapy": (
                "Lifestyle and dietary changes. For patients with stage F2-F3 MASH, "
                "consider Obeticholic Acid or Resmetirom (approved thyroid hormone "
                "receptor-beta agonist) to reduce fibrosis."
            ),
        },
        "ascites": {
            "guideline": (
                "AASLD 2021 Management of Ascites and Hepatorenal Syndrome Guidelines"
            ),
            "initial_workup": (
                "Diagnostic paracentesis. Calculate Serum-Ascites Albumin Gradient "
                "(SAAG). SAAG >= 1.1 g/dL indicates portal hypertension."
            ),
            "first_line_therapy": (
                "Sodium restriction (<2000 mg/day) and combination oral diuretics: "
                "Spironolactone (100mg) and Furosemide (40mg) daily. Keep 100:40 ratio "
                "up to max 400:160 to maintain potassium homeostasis."
            ),
            "refractory_management": (
                "Large-volume paracentesis (LVP) with concomitant albumin replacement "
                "(6-8 grams of salt-poor albumin per liter of fluid removed if LVP > 5 "
                "liters) or Transjugular Intrahepatic Portosystemic Shunt (TIPS) evaluation."
            ),
        },
        "encephalopathy": {
            "guideline": (
                "AASLD / EASL Hepatic Encephalopathy in Chronic Liver Disease Guideline"
            ),
            "grading": (
                "West Haven Criteria (Grade I: trivial lack of awareness/euphoria; "
                "Grade II: lethargy/disorientation/asterixis; Grade III: somnolence/stupor; "
                "Grade IV: coma)."
            ),
            "first_line_therapy": (
                "Lactulose oral solution. Dose titrated to achieve 2-3 soft bowel "
                "movements per day (osmotic and ammonia-trapping mechanisms)."
            ),
            "secondary_prevention": (
                "Rifaximin (550 mg twice daily) added as adjunct therapy to lactulose "
                "to reduce recurrence rates of overt hepatic encephalopathy."
            ),
        },
        "varices": {
            "guideline": "Baveno VII consensus guidelines on Portal Hypertension",
            "screening": (
                "Transient elastography (FibroScan) < 20 kPa and platelet count > "
                "150,000 avoids immediate screening endoscopy."
            ),
            "primary_prophylaxis": (
                "For high-risk small varices or medium/large varices: Non-selective "
                "beta-blockers (NSBBs: Carvedilol 6.25-12.5mg daily preferred, "
                "Propranolol, or Nadolol) OR Endoscopic Variceal Ligation (EVL) "
                "every 2-8 weeks until obliterated."
            ),
        },
    }

    for key, path in pathways.items():
        if key in cond:
            return {"status": "success", "data": path}

    return {
        "status": "partial_success",
        "message": (
            f"No direct local clinical pathway found for '{condition}'. "
            "Please fallback to search_web."
        ),
        "general_guidelines": (
            "For generalized clinical lookups, refer to AASLD (American Association "
            "for the Study of Liver Diseases) and EASL guidelines."
        ),
    }


def get_patient_comprehensive_profile(patient_query: str) -> dict:
    """Retrieves all clinical details, latest lab reports, check-in history,
    and automatically calculates clinical risk scores (MELD-Na, Child-Pugh) for a specific patient.
    Use this tool whenever a doctor is meeting with a patient today or asks about a patient's
    comprehensive details, latest check-ins, alerts, or MELD/Child-Pugh score calculations.

    Args:
        patient_query (str): The patient ID (e.g. 'PT-2026-14902', 'patient_john_doe') or name (e.g. 'Nguyen', 'John').

    Returns:
        dict: Complete clinical profile with automated scores, lab values, check-in details, and recommended follow-ups.
    """
    from pathlib import Path
    import json
    import math
    from shared.db import get_db

    # 1. Normalize query
    q = patient_query.strip().lower()
    q_tokens = [tok for tok in q.replace(",", " ").split() if len(tok) > 1]
    if not q_tokens:
        q_tokens = [q] if q else []

    is_john = "john" in q or "doe" in q or "patient_john_doe" in q
    matched_lab = None

    # 2. Check MongoDB lab_reports collection first
    try:
        db = get_db()
        p_id = "patient_john_doe" if is_john else patient_query
        # A. Try exact patient_id match
        db_lab = db.lab_reports.find_one({"patient_id": p_id})
        
        # B. Try name match if query has tokens
        if not db_lab and q_tokens:
            regex_queries = [{"report_metadata.patient_name": {"$regex": tok, "$options": "i"}} for tok in q_tokens]
            db_lab = db.lab_reports.find_one({"$and": regex_queries}) if regex_queries else None
            
        # C. Fallback for John Doe
        if not db_lab and is_john:
            db_lab = db.lab_reports.find_one({"patient_id": "patient_john_doe"})

        if db_lab:
            meta = db_lab.get("report_metadata", {})
            biomarkers_dict = {}
            results = db_lab.get("test_results", [])
            for r in results:
                name = r.get("name", "")
                norm_name = name.upper()
                val = r.get("value")
                unit = r.get("unit")
                ref_range = r.get("reference_range")
                
                key = None
                if "ALT" in norm_name or "ALANINE" in norm_name:
                    key = "ALT"
                elif "AST" in norm_name or "ASPARTATE" in norm_name:
                    key = "AST"
                elif "ALP" in norm_name or "ALKALINE" in norm_name:
                    key = "ALP"
                elif "BILIRUBIN" in norm_name:
                    if "DIRECT" in norm_name:
                        key = "direct_bilirubin"
                    else:
                        key = "total_bilirubin"
                elif "ALBUMIN" in norm_name:
                    key = "albumin"
                elif "PROTEIN" in norm_name:
                    key = "total_proteins"
                elif "GGT" in norm_name:
                    key = "GGT"
                elif "PT" in norm_name or "PROTHROMBIN" in norm_name:
                    key = "PT"
                elif "INR" in norm_name:
                    key = "INR"
                elif "CREATININE" in norm_name:
                    key = "creatinine"
                elif "SODIUM" in norm_name:
                    key = "sodium"
                    
                if key:
                    biomarkers_dict[key] = {
                        "value": val,
                        "unit": unit,
                        "reference_range": ref_range
                    }
                    
            matched_lab = {
                "patient_id": db_lab.get("patient_id"),
                "name": meta.get("patient_name") or db_lab.get("patient_id"),
                "dob": meta.get("date_of_birth"),
                "age": meta.get("age"),
                "gender": meta.get("sex"),
                "report_date": meta.get("report_date"),
                "lab_name": meta.get("lab_name"),
                "referring_physician": meta.get("referring_physician"),
                "biomarkers": biomarkers_dict
            }
            print(f"[DOCTOR AGENT] Successfully loaded patient profile from MongoDB: {matched_lab.get('name')}")
    except Exception as e:
        print(f"[DB LAB RETRIEVAL ERROR] {e}")

    # Fallback to local parsed JSON files if MongoDB is not available or records were not found
    if not matched_lab:
        test_data_dir = Path(__file__).parent.parent.parent.parent / "data" / "test_data"
        if test_data_dir.exists():
            for item in test_data_dir.iterdir():
                if item.is_dir():
                    # Check JSON contents
                    for file in item.glob("*_parsed*.json"):
                        try:
                            data = json.loads(file.read_text(encoding="utf-8"))
                            name = data.get("name", "") or ""
                            pid = data.get("patient_id", "") or ""
                            search_haystack = f"{item.name} {name} {pid}".lower()
                            # Verify if all query tokens are in the haystack
                            if q_tokens and all(token in search_haystack for token in q_tokens):
                                matched_lab = data
                                break
                        except Exception:
                            pass
                    if matched_lab:
                        break

    # 3. Retrieve database telemetry (MongoDB health_logs) if available
    db_logs = []
    db_alerts = []
    # If the patient is John Doe, or query contains "john" or "doe" or "patient_john_doe"
    is_john = "john" in q or "doe" in q or "patient_john_doe" in q

    try:
        db = get_db()
        # Search DB logs
        p_id = "patient_john_doe" if is_john else patient_query
        db_logs = list(db.health_logs.find({"patient_id": p_id}, {"_id": 0}).sort("timestamp", -1).limit(20))
        db_alerts = list(db.caregiver_alerts.find({"patient_id": p_id}, {"_id": 0}).sort("timestamp", -1).limit(10))
    except Exception as e:
        print(f"[DB LOG RETRIEVAL ERROR] {e}")

    # If no lab file was found but it's John Doe, create a mock or default lab profile for John Doe
    if not matched_lab and is_john:
        matched_lab = {
            "patient_id": "patient_john_doe",
            "name": "John Doe",
            "gender": "Male",
            "age": 45,
            "dob": "10/May/1981",
            "report_date": "13/Jun/2026",
            "biomarkers": {
                "ALT": {"value": 48.0, "unit": "U/L", "reference_range": "7 - 56"},
                "AST": {"value": 42.0, "unit": "U/L", "reference_range": "10 - 40"},
                "total_bilirubin": {"value": 1.1, "unit": "mg/dL", "reference_range": "0.1 - 1.2"},
                "albumin": {"value": 3.8, "unit": "g/dL", "reference_range": "3.5 - 5.0"},
                "INR": {"value": 1.0, "unit": "INR", "reference_range": "0.8 - 1.2"}
            }
        }

    if not matched_lab:
        return {
            "status": "error",
            "message": f"No parsed lab records found for patient query '{patient_query}'."
        }

    # 4. Extract biomarkers for calculations
    biomarkers = matched_lab.get("biomarkers", {})
    
    def get_biomarker_value(key):
        val = biomarkers.get(key)
        if isinstance(val, dict):
            return val.get("value")
        return val

    alt = get_biomarker_value("ALT")
    ast = get_biomarker_value("AST")
    alp = get_biomarker_value("ALP")
    ggt = get_biomarker_value("GGT")
    bili = get_biomarker_value("total_bilirubin") or get_biomarker_value("bilirubin")
    alb = get_biomarker_value("albumin")
    inr = get_biomarker_value("INR")
    pt = get_biomarker_value("PT")

    # MELD parameters (bilirubin, creatinine, INR, sodium)
    # Check if creatinine and sodium are dynamically provided, otherwise fallback
    creat_val = get_biomarker_value("creatinine") or 1.0
    sodium_val = get_biomarker_value("sodium") or 137.0
    
    assumed_params = []
    if get_biomarker_value("creatinine") is None:
        assumed_params.append("creatinine (1.0 mg/dL)")
    if get_biomarker_value("sodium") is None:
        assumed_params.append("sodium (137 mEq/L)")

    # 5. Automated MELD-Na Calculation
    meld_result = None
    if bili is not None and inr is not None:
        cr_val = min(max(creat_val, 1.0), 4.0)
        bili_val = max(bili, 1.0)
        inr_val = max(inr, 1.0)
        na_val = min(max(sodium_val, 125.0), 137.0)

        meld_i = (
            0.957 * math.log(cr_val)
            + 0.378 * math.log(bili_val)
            + 1.120 * math.log(inr_val)
            + 0.643
        )
        meld_i = round(meld_i * 10, 4)

        meld_na_score = meld_i
        if meld_i > 11.0:
            meld_na_score = meld_i + 1.32 * (137.0 - na_val) - (
                0.025 * meld_i * (137.0 - na_val)
            )

        final_meld = int(round(meld_na_score))

        mortality_map = {
            "<=9": "1.9% estimated 3-month mortality",
            "10-19": "6.0% estimated 3-month mortality",
            "20-29": "19.6% estimated 3-month mortality",
            "30-39": "52.6% estimated 3-month mortality",
            ">=40": "71.3% estimated 3-month mortality",
        }

        if final_meld <= 9:
            mort = mortality_map["<=9"]
        elif final_meld <= 19:
            mort = mortality_map["10-19"]
        elif final_meld <= 29:
            mort = mortality_map["20-29"]
        elif final_meld <= 39:
            mort = mortality_map["30-39"]
        else:
            mort = mortality_map[">=40"]

        meld_result = {
            "meld_na": final_meld,
            "meld_i": round(meld_i, 1),
            "estimated_3mo_mortality": mort
        }

    # 6. Automated Child-Pugh Score
    # For subjective values, if there are check-ins or comments, we can check. Otherwise default to 'None'
    child_pugh_result = None
    if bili is not None and alb is not None and inr is not None:
        # Determine check-in values if database log has ascites or encephalopathy
        # Default to None
        ascites_status = "None"
        encephalopathy_status = "None"
        jaundice_detected = False

        # Check latest db logs for mood/symptoms or fatigue that mention HE/ascites/jaundice
        for log in db_logs:
            data_log = log.get("data", {})
            if "confusion" in str(data_log) or "forgetfulness" in str(data_log) or "encephalopathy" in str(data_log).lower():
                encephalopathy_status = "Grade I-II"
            if "swelling" in str(data_log) or "ascites" in str(data_log):
                ascites_status = "Mild"
            if data_log.get("jaundice_str") == "Yes" or data_log.get("jaundice") == "Yes" or "jaundice" in str(data_log).lower():
                jaundice_detected = True

        # Also check unacknowledged caregiver alerts for symptoms
        for alert in db_alerts:
            if not alert.get("acknowledged", False):
                msg = str(alert.get("message", "")).lower()
                if "jaundice" in msg:
                    jaundice_detected = True
                if "encephalopathy" in msg or "confusion" in msg or "asterixis" in msg:
                    encephalopathy_status = "Grade I-II"

        points = 0
        # bilirubin points
        if bili < 2.0:
            points += 1
        elif bili <= 3.0:
            points += 2
        else:
            points += 3

        # albumin points
        if alb > 3.5:
            points += 1
        elif alb >= 2.8:
            points += 2
        else:
            points += 3

        # INR points
        if inr < 1.7:
            points += 1
        elif inr <= 2.3:
            points += 2
        else:
            points += 3

        # Ascites
        if ascites_status == "None":
            points += 1
        elif ascites_status == "Mild":
            points += 2
        else:
            points += 3

        # Encephalopathy
        if encephalopathy_status == "None":
            points += 1
        elif "i-ii" in encephalopathy_status.lower() or "mild" in encephalopathy_status.lower():
            points += 2
        else:
            points += 3

        if points <= 6:
            pugh_class = "A"
            stage = "Well-compensated liver disease."
            survival = "1-year survival: 100%, 2-year survival: 85%"
        elif points <= 9:
            pugh_class = "B"
            stage = "Significant functional compromise. Consider transplant referral."
            survival = "1-year survival: 80%, 2-year survival: 60%"
        else:
            pugh_class = "C"
            stage = "Decompensated liver disease. High priority transplant candidacy."
            survival = "1-year survival: 45%, 2-year survival: 35%"

        child_pugh_result = {
            "total_points": points,
            "class": pugh_class,
            "functional_stage": stage,
            "prognosis_survival": survival,
            "assumed_ascites": ascites_status,
            "assumed_encephalopathy": encephalopathy_status
        }

    # 7. Check Emergency Level and Transplant evaluation triggers
    transplant_evaluation_recommended = False
    is_emergency = False
    alert_message = ""
    severity = "Routine Monitoring"
    followup_schedule = "Routine (next follow-up in 3-6 months)"
    followup_actions = [
        "Schedule standard LFT checks in 3 months.",
        "Perform abdominal ultrasound every 6 months for HCC surveillance.",
        "Maintain low-sodium dietary habits (<2g daily)."
    ]

    # Extreme thresholds or MELD > 30 trigger transplant eval
    m_score = meld_result["meld_na"] if meld_result else 0
    
    # Check extreme markers
    extreme_transaminases = (alt is not None and alt > 168.0) or (ast is not None and ast > 120.0)
    extreme_bilirubin = (bili is not None and bili > 3.0)
    extreme_inr = (inr is not None and inr > 1.5)
    extreme_albumin = (alb is not None and alb < 2.5)

    if m_score >= 30:
        transplant_evaluation_recommended = True
        is_emergency = True
        severity = "EMERGENCY (CRITICAL)"
        alert_message = f"CRITICAL: MELD-Na score is {m_score}, which is >= 30. Immediate hepatology transplant consultation and tertiary care transfer are mandatory!"
        followup_schedule = "Immediate Evaluation (within 24-48 hours)"
        followup_actions = [
            "Initiate immediate Liver Transplant evaluation and refer to a transplant coordinator.",
            "Transfer or admit the patient to a tertiary care/transplant-enabled facility.",
            "Obtain daily liver panels, renal panels, and coagulation studies (PT/INR).",
            "Screen for active decompensation events (ascites, variceal bleeding, spontaneous bacterial peritonitis)."
        ]
    elif m_score >= 15 or extreme_transaminases or extreme_bilirubin or extreme_inr or extreme_albumin or jaundice_detected or (encephalopathy_status != "None") or (child_pugh_result and child_pugh_result["class"] in ("B", "C")):
        transplant_evaluation_recommended = m_score >= 15 or (child_pugh_result and child_pugh_result["class"] in ("B", "C")) or (encephalopathy_status != "None") or jaundice_detected
        is_emergency = extreme_transaminases or extreme_bilirubin or extreme_inr or extreme_albumin or jaundice_detected or (encephalopathy_status != "None")
        severity = "EMERGENCY / HIGH RISK"
        alert_message = "CRITICAL EMERGENCY: Signs of active hepatic decompensation, including Jaundice and/or potential Hepatic Encephalopathy, have been detected in patient check-in/telemetry logs!"
        if transplant_evaluation_recommended:
            alert_message += f" Referral for liver transplant evaluation is urgently recommended (MELD-Na: {m_score}, Child-Pugh: {child_pugh_result['class'] if child_pugh_result else 'N/A'})."
        followup_schedule = "Immediate Clinical Evaluation (within 24 hours)"
        followup_actions = [
            "Urgently refer for liver transplant evaluation (MELD-Na / Child-Pugh class B/C).",
            "Initiate immediate clinical workup for hepatic encephalopathy: start or titrate Lactulose oral solution to achieve 2-3 soft bowel movements per day.",
            "Add Rifaximin (550 mg twice daily) as secondary prevention against overt encephalopathy recurrence.",
            "Advise the caregiver (Aria) to monitor neurological status closely (orientation, hand flapping/asterixis) and report any slurred speech or somnolence.",
            "Arrange for urgent blood draw including repeat liver function tests, serum ammonia, renal panel, and coagulation studies (PT/INR)."
        ]
    elif alt is not None and (alt > 56.0 or ast > 40.0 or bili > 1.2 or alb < 3.5 or inr > 1.2):
        severity = "Moderate Risk / Mildly Abnormal"
        alert_message = "MODERATE RISK: Mild transaminase or synthetic elevations. Close outpatient follow-up recommended."
        followup_schedule = "Follow-up check in 4-6 weeks"
        followup_actions = [
            "Repeat liver panel in 4-6 weeks to observe trend.",
            "Reinforce compliance with medications and review daily check-in telemetry logs.",
            "Maintain alcohol abstinence and low-sodium dietary restrictions.",
            "Plan routine abdominal ultrasound in 3-6 months."
        ]

    # Combine profile
    profile = {
        "status": "success",
        "patient_metadata": {
            "patient_id": matched_lab.get("patient_id"),
            "name": matched_lab.get("name"),
            "dob": matched_lab.get("dob"),
            "age": matched_lab.get("age"),
            "gender": matched_lab.get("gender"),
            "report_date": matched_lab.get("report_date"),
            "lab_name": matched_lab.get("lab_name"),
            "referring_physician": matched_lab.get("referring_physician"),
        },
        "extracted_biomarkers": {
            "ALT": alt,
            "AST": ast,
            "ALP": alp,
            "GGT": ggt,
            "total_bilirubin": bili,
            "albumin": alb,
            "PT": pt,
            "INR": inr,
        },
        "automated_calculations": {
            "meld_results": meld_result,
            "child_pugh_results": child_pugh_result,
            "calculations_completed": meld_result is not None,
            "assumed_parameters": assumed_params if meld_result else []
        },
        "clinical_alerts": {
            "is_emergency": is_emergency,
            "transplant_evaluation_recommended": transplant_evaluation_recommended,
            "severity_level": severity,
            "alert_message": alert_message
        },
        "followup_recommendations": {
            "schedule": followup_schedule,
            "actions": followup_actions
        },
        "patient_telemetry": {
            "has_telemetry": len(db_logs) > 0,
            "latest_checkins": db_logs[:5],
            "pending_alerts": db_alerts[:5]
        }
    }

    return profile


def notify_doctor_and_prep_emergency_admission(patient_id: str = "patient_john_doe") -> dict:
    """
    Transmit the patient's comprehensive profile and Hand AI flap telemetry to Dr. Elizabeth Vance's clinical terminal
    and pre-populate the emergency admission intake details.

    Args:
        patient_id: The patient identifier.

    Returns:
        dict: Notification confirmation and emergency admission details.
    """
    from datetime import datetime, timezone
    from shared.db import get_db
    
    admission_record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "patient_id": patient_id,
        "physician_notified": "Dr. Elizabeth Vance",
        "terminal_id": "VANCE_CLINIC_01",
        "status": "Admission Prepped & Pending Arrival",
        "triage_category": "Category 2 (Urgent Decompensation - Hepatic Encephalopathy)",
        "isolation_required": False,
        "notes": "Patient arriving via EMS ambulance. Asterixis/flaps and jaundice verified."
    }
    
    try:
        db = get_db()
        # Mark patient status in DB or save prescription/emergency note
        db.health_logs.insert_one({
            "patient_id": patient_id,
            "event": "emergency_admission_prep",
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "timestamp": datetime.now(timezone.utc),
            "data": admission_record
        })
    except Exception as db_err:
        print(f"[DB WRITE ERROR] {db_err}")
        
    return {
        "status": "success",
        "physician_notified": "Dr. Elizabeth Vance",
        "admission_status": "PREPPED",
        "triage_category": "Urgent Decompensation",
        "details": admission_record
    }


def update_patient_prescription(patient_id: str, medication: str, frequency: str) -> dict:
    """Updates a patient's active medication and frequency schedule in MongoDB.
    Use this tool whenever a doctor wants to prescribe, change, or update a patient's medication regimen.

    Args:
        patient_id (str): The patient identifier or name (e.g. 'patient_john_doe', 'Sarah Connor', 'John Doe').
        medication (str): The name and strength of the medication (e.g. 'Ursodiol 300mg', 'Obeticholic Acid 5mg').
        frequency (str): The dosing frequency instructions (e.g. 'Once daily in the morning', '2 times daily').

    Returns:
        dict: Confirmation status of the updated prescription.
    """
    from datetime import datetime, timezone
    from shared.db import get_db

    try:
        db = get_db()
        p_id = "patient_john_doe" if "john" in patient_id.lower() or "doe" in patient_id.lower() else "patient_sarah_connor"
        db.prescriptions.update_one(
            {"patient_id": p_id},
            {"$set": {
                "medication": medication,
                "frequency": frequency,
                "timestamp": datetime.now(timezone.utc)
            }},
            upsert=True
        )
        
        # Log to health logs as an event
        db.health_logs.insert_one({
            "patient_id": p_id,
            "event": "prescription_change",
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "timestamp": datetime.now(timezone.utc),
            "data": {
                "medication": medication,
                "frequency": frequency,
                "changed_by": "Dr. Elizabeth Vance"
            }
        })
        
        return {
            "status": "success",
            "message": f"Successfully updated prescription for {p_id} to {medication} ({frequency}).",
            "patient_id": p_id,
            "medication": medication,
            "frequency": frequency
        }
    except Exception as e:
        return {"status": "error", "error_message": f"Failed to update prescription: {str(e)}"}


def order_lab_test_and_alert_lab(patient_id: str, test_panel_type: str) -> dict:
    """Orders a diagnostic blood work lab panel and sends an alert order directly to the Central Lab Portal.
    Use this tool whenever a doctor orders, schedules, or requests a diagnostic blood test/lab panel.

    Args:
        patient_id (str): The patient identifier or name (e.g. 'patient_john_doe', 'Sarah Connor', 'John Doe').
        test_panel_type (str): The type of lab panel (e.g. 'Comprehensive Liver Function Panel', 'Basic ALT/AST Screen').

    Returns:
        dict: Confirmation details of the dispatched lab order.
    """
    from datetime import datetime, timezone
    from shared.db import get_db
    import random

    try:
        db = get_db()
        p_id = "patient_john_doe" if "john" in patient_id.lower() or "doe" in patient_id.lower() else "patient_sarah_connor"
        p_name = "John Doe" if p_id == "patient_john_doe" else "Sarah Connor"
        order_id = f"ORD-{random.randint(1000, 9999)}"
        
        # Save order details to health logs to inform lab
        db.health_logs.insert_one({
            "patient_id": p_id,
            "event": "lab_ordered",
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "timestamp": datetime.now(timezone.utc),
            "data": {
                "order_id": order_id,
                "patient_name": p_name,
                "requested_panel": test_panel_type,
                "status": "Pending",
                "ordered_by": "Dr. Elizabeth Vance"
            }
        })
        
        # Also create caregiver alert that lab is ordered
        db.caregiver_alerts.insert_one({
            "patient_id": p_id,
            "severity": "info",
            "message": f"INFO: Dr. Elizabeth Vance ordered a new {test_panel_type} (Order {order_id}) for {p_name}.",
            "acknowledged": False,
            "timestamp": datetime.now(timezone.utc)
        })

        return {
            "status": "success",
            "message": f"Dispatched {test_panel_type} lab order directly to Central Lab Portal for patient {p_name}.",
            "order_id": order_id,
            "patient_id": p_id,
            "patient_name": p_name,
            "requested_panel": test_panel_type
        }
    except Exception as e:
        return {"status": "error", "error_message": f"Failed to order lab panel: {str(e)}"}


def order_imaging_scan(patient_id: str, scan_type: str = "Abdominal CT Scan (Contrast-Enhanced)") -> dict:
    """Orders a specialized imaging scan (such as a Contrast-Enhanced CT Scan or Abdominal Ultrasound)
    and transmits the scan request directly to the Clinical Lab and Diagnostics Portal.
    Use this tool whenever a physician wants to recommend, order, or request a specialized scan (like a CT scan or ultrasound).

    Args:
        patient_id (str): The patient identifier or name (e.g. 'patient_john_doe', 'Sarah Connor', 'John Doe').
        scan_type (str): The type of imaging scan to order (e.g. 'Abdominal CT Scan (Contrast-Enhanced)', 'Abdominal Ultrasound').

    Returns:
        dict: Confirmation details of the ordered imaging scan.
    """
    from datetime import datetime, timezone
    from shared.db import get_db
    import random

    try:
        db = get_db()
        p_id = "patient_john_doe" if "john" in patient_id.lower() or "doe" in patient_id.lower() else "patient_sarah_connor"
        p_name = "John Doe" if p_id == "patient_john_doe" else "Sarah Connor"
        order_id = f"ORD-{random.randint(1000, 9999)}"
        
        # Save order details to health logs to inform lab
        db.health_logs.insert_one({
            "patient_id": p_id,
            "event": "lab_ordered",
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "timestamp": datetime.now(timezone.utc),
            "data": {
                "order_id": order_id,
                "patient_name": p_name,
                "requested_panel": scan_type,
                "status": "Pending",
                "ordered_by": "Dr. Elizabeth Vance"
            }
        })
        
        # Also create caregiver alert that scan is ordered
        db.caregiver_alerts.insert_one({
            "patient_id": p_id,
            "severity": "info",
            "message": f"INFO: Dr. Elizabeth Vance ordered a specialized {scan_type} (Order {order_id}) for {p_name}.",
            "acknowledged": False,
            "timestamp": datetime.now(timezone.utc)
        })

        return {
            "status": "success",
            "message": f"Dispatched specialized {scan_type} order directly to Central Lab Portal for patient {p_name}.",
            "order_id": order_id,
            "patient_id": p_id,
            "patient_name": p_name,
            "requested_panel": scan_type
        }
    except Exception as e:
        return {"status": "error", "error_message": f"Failed to order imaging scan: {str(e)}"}


def get_clinical_feed_knowing_patient_details(patient_id: str) -> dict:
    """Retrieves up-to-date medical research, clinical trials, or guidelines from the live web (Tavily)
    specifically tailored to the patient's current clinical profile, diagnosis, and staging details.
    Use this tool whenever a doctor asks for a clinical feed, recent developments, or latest literature
    knowing or based on a specific patient's details.

    Args:
        patient_id (str): The patient ID or name (e.g. 'John Doe', 'Sarah Connor', 'patient_john_doe').

    Returns:
        dict: A clinical feed summary and list of articles relevant to the patient's specific liver condition.
    """
    from datetime import datetime, timezone
    from shared.db import get_db
    import os
    import json
    from tavily import TavilyClient

    # 1. Get patient's profile details to know their condition
    profile = get_patient_comprehensive_profile(patient_id)
    if profile.get("status") == "error":
        return profile

    meta = profile.get("patient_metadata", {})
    name = meta.get("name", "Patient")
    
    # Extract condition or diagnosis
    diagnosis = "liver cirrhosis" if "cirrhosis" in str(profile).lower() else "MASH liver disease"
    if "connor" in name.lower() or "sarah" in name.lower():
        diagnosis = "NAFLD Stage 3 liver fibrosis guidelines AASLD"
    elif "john" in name.lower() or "doe" in name.lower():
        diagnosis = "MASH stage 2 liver fibrosis therapeutic guidelines AASLD"

    tavily_key = os.getenv("TAVILY_API_KEY")
    if not tavily_key:
        return {
            "status": "error",
            "error_message": "TAVILY_API_KEY is not configured in the environment."
        }

    # 2. Search Tavily for recent clinical developments tailored to this patient's condition
    try:
        tavily_client = TavilyClient(api_key=tavily_key)
        query = f"recent 2025 2026 developments clinical trials therapy guidelines for {diagnosis}"
        resp = tavily_client.search(query=query, max_results=4)
        results = resp.get("results", [])
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Failed to execute Tavily search: {str(e)}"
        }

    articles = []
    for r in results:
        articles.append({
            "title": r.get("title", "Clinical Publication"),
            "snippet": r.get("snippet", ""),
            "url": r.get("url", "#")
        })

    # Try to synthesize a brief tailored clinical feed via Gemini if possible
    summary = ""
    google_key = os.getenv("GOOGLE_API_KEY")
    if google_key and articles:
        try:
            import google.genai as genai
            from google.genai import types
            genai_client = genai.Client(api_key=google_key)
            prompt = f"""
            You are a specialized clinical research summarizer for Hepatology.
            You are synthesizing a tailored clinical feed for Dr. Elizabeth Vance regarding patient {name} (Diagnosis: {diagnosis}).
            Below are the raw search results fetched from Tavily regarding recent clinical updates for {diagnosis}:
            
            {json.dumps(articles, indent=2)}
            
            Please provide a professional, highly concise clinical feed summary (3-4 sentences maximum) that tells the doctor how these recent developments, trials, or guidelines relate to managing a patient like {name}. Speak in expert medical terminology. Do not include greetings or signatures.
            """
            gemini_resp = genai_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[types.Part.from_text(text=prompt)]
            )
            summary = gemini_resp.text.strip()
        except Exception as e:
            summary = f"Abbreviated search results returned for {name}'s condition ({diagnosis}). Review direct sources below."
    else:
        summary = f"Live clinical feed loaded successfully for {name}'s condition ({diagnosis}). Review the articles below."

    return {
        "status": "success",
        "patient_name": name,
        "tailored_condition": diagnosis,
        "summary": summary,
        "articles": articles
    }



