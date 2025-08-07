import os, json, time, argparse, requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = os.getenv("BASE_ID")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

HEADERS = {
    "Authorization": f"Bearer {AIRTABLE_API_KEY}",
    "Content-Type": "application/json"
}

TIER1 = {"Google", "Meta", "OpenAI"}
LOCATIONS = {"US", "Canada", "UK", "Germany", "India"}

def log(msg): print(f"[INFO] {msg}")
def error(msg): print(f"[ERROR] {msg}")

def fetch_records(table):
    url = f"https://api.airtable.com/v0/{BASE_ID}/{table}"
    resp = requests.get(url, headers=HEADERS)
    return resp.json().get('records', []) if resp.status_code == 200 else []

def create_record(table, fields):
    url = f"https://api.airtable.com/v0/{BASE_ID}/{table}"
    resp = requests.post(url, headers=HEADERS, json={"fields": fields})
    if resp.status_code != 200:
        error(f"Create failed: {resp.text}")
    return resp.json()

def update_record(table, record_id, fields):
    url = f"https://api.airtable.com/v0/{BASE_ID}/{table}/{record_id}"
    resp = requests.patch(url, headers=HEADERS, json={"fields": fields})
    if resp.status_code != 200:
        error(f"Update failed: {resp.text}")
    return resp.json()

def compress():
    log("Starting compression...")
    applicants = fetch_records("Applicants")
    for applicant in applicants:
        try:
            aid = applicant["id"]
            personal = [r["fields"] for r in fetch_records("Personal Details") if r["fields"].get("Applicant") == [aid]]
            work = [r["fields"] for r in fetch_records("Work Experience") if r["fields"].get("Applicant") == [aid]]
            salary = [r["fields"] for r in fetch_records("Salary Preferences") if r["fields"].get("Applicant") == [aid]]
            compressed = {
                "personal": personal[0] if personal else {},
                "experience": work,
                "salary": salary[0] if salary else {}
            }
            update_record("Applicants", aid, {"Compressed JSON": json.dumps(compressed)})
            log(f"Compressed Applicant {aid}")
        except Exception as e:
            error(f"Compression failed for {aid}: {e}")

def decompress():
    log("Starting decompression...")
    applicants = fetch_records("Applicants")
    for applicant in applicants:
        try:
            aid = applicant["id"]
            compressed = json.loads(applicant["fields"].get("Compressed JSON", "{}"))
            if compressed.get("personal"):
                create_record("Personal Details", {**compressed["personal"], "Applicant": [aid]})
            for w in compressed.get("experience", []):
                create_record("Work Experience", {**w, "Applicant": [aid]})
            if compressed.get("salary"):
                create_record("Salary Preferences", {**compressed["salary"], "Applicant": [aid]})
            log(f"Decompressed Applicant {aid}")
        except Exception as e:
            error(f"Decompression failed for {aid}: {e}")

def shortlist():
    log("Starting shortlisting...")
    applicants = fetch_records("Applicants")
    for applicant in applicants:
        try:
            aid = applicant["id"]
            data = json.loads(applicant["fields"].get("Compressed JSON", "{}"))
            if not data: continue

            experience = data.get("experience", [])
            years = 0
            for e in experience:
                years += 1 if e.get("Company") else 0
            worked_tier1 = any(e.get("Company") in TIER1 for e in experience)
            comp = data.get("salary", {})
            loc = data.get("personal", {}).get("Location")

            if (years >= 4 or worked_tier1) and comp.get("Preferred Rate", 999) <= 100 and \
               comp.get("Availability (hrs/wk)", 0) >= 20 and loc in LOCATIONS:
                reason = "Tier1 Experience + Comp & Availability + Location match"
                create_record("Shortlisted Leads", {
                    "Applicant": [aid],
                    "Compressed JSON": json.dumps(data),
                    "Score Reason": reason
                })
                log(f"Shortlisted Applicant {aid}")
        except Exception as e:
            error(f"Shortlist failed for {aid}: {e}")

def call_groq_with_retry(prompt_json, retries=3):
    if not GROQ_API_KEY:
        raise Exception("Missing GROQ_API_KEY in environment.")
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    body = {
        "model": "llama3-8b-8192",
        "messages": [
            {"role": "system", "content": "You are a recruiting analyst. Given this JSON applicant profile, do four things:\n1. Provide a concise 75-word summary.\n2. Rate overall candidate quality from 1-10 (higher is better).\n3. List any data gaps or inconsistencies you notice.\n4. Suggest up to three follow-up questions to clarify gaps.\n\nReturn exactly:\nSummary: <text>\nScore: <integer>\nIssues: <comma-separated list or 'None'>\nFollow-Ups: <bullet list>"},
            {"role": "user", "content": prompt_json}
        ],
        "temperature": 0.3,
        "max_tokens": 300
    }

    for attempt in range(retries):
        try:
            resp = requests.post(url, headers=headers, json=body)
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            else:
                error(f"GROQ call failed ({resp.status_code}): {resp.text}")
        except Exception as e:
            error(f"Exception: {e}")
        time.sleep(2 ** attempt)
    return None

def enrich():
    log("Starting LLM enrichment...")
    applicants = fetch_records("Applicants")
    for applicant in applicants:
        try:
            aid = applicant["id"]
            compressed = json.loads(applicant["fields"].get("Compressed JSON", "{}"))
            if not compressed:
                log(f"Skipping {aid}: no JSON.")
                continue
            llm_output = call_groq_with_retry(json.dumps(compressed))
            if not llm_output:
                error(f"LLM failed for {aid}")
                continue

            summary, score, followups = "", "", ""
            for line in llm_output.splitlines():
                if line.startswith("Summary:"): summary = line.replace("Summary:", "").strip()
                elif line.startswith("Score:"): score = line.replace("Score:", "").strip()
                elif line.startswith("Follow-Ups:"): followups = line.replace("Follow-Ups:", "").strip()

            update_record("Applicants", aid, {
                "LLM Summary": summary,
                "LLM Score": int(score) if score.isdigit() else None,
                "LLM Follow-Ups": followups
            })
            log(f"Enriched Applicant {aid}")
        except Exception as e:
            error(f"Enrichment failed for {aid}: {e}")

# Entrypoint
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage Airtable Contractor Applications")
    parser.add_argument("action", choices=["compress", "decompress", "shortlist", "enrich"])
    args = parser.parse_args()

    if args.action == "compress": compress()
    elif args.action == "decompress": decompress()
    elif args.action == "shortlist": shortlist()
    elif args.action == "enrich": enrich()
