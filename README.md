# Airtable Automation

A complete Airtable + Python automation system for managing contractor applications. It supports:

- Multi-table data collection and compression into a single JSON object
- JSON decompression into normalized child records
- Auto-shortlisting candidates based on multi-factor rules
- Integration with Groq LLMs for summarization, scoring, and follow-ups

---

## Features

- Airtable schema: Applicants + linked Personal Details, Work Experience, Salary Preferences
- Compression & decompression of data using Airtable API
- Smart shortlisting based on experience, availability, rate, and location
- LLM enrichment with Groq's `llama3-8b-8192`
- CLI automation using Python + `argparse`

---

## Setup

## Create Environment
python -m venv venv
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows

## Install dependencies
pip install -r requirements.txt

## Create .env file
AIRTABLE_API_KEY=your_airtable_api_key
BASE_ID=your_airtable_base_id
GROQ_API_KEY=your_groq_api_key

## Usage
Run any of the following commands:

python manage.py compress     # Merge tables into compressed JSON
python manage.py decompress   # Restore records from compressed JSON
python manage.py shortlist    # Evaluate and tag promising applicants
python manage.py enrich       # Summarize, score, and follow-up via Groq

## Prompt for Groq LLM
You are a recruiting analyst. Given this JSON applicant profile, do four things:
1. Provide a concise 75-word summary.
2. Rate overall candidate quality from 1-10 (higher is better).
3. List any data gaps or inconsistencies you notice.
4. Suggest up to three follow-up questions to clarify gaps.

Return exactly:
Summary: <text>
Score: <integer>
Issues: <comma-separated list or 'None'>
Follow-Ups: <bullet list>

## Project Structure
mercor-airtable-automation/
│
├── manage.py                  # Main CLI script with all core logic
├── .env                       # Environment variables (not committed)
├── requirements.txt           # Python dependencies
├── README.md                  # Project overview and setup instructions
├── .gitignore                 # Ignore virtual envs, .env, etc.

