import os
import requests
from dotenv import load_dotenv

# Load env
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

headers = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json",
}

data = {
    "model": "llama3-8b-8192",
    "messages": [{"role": "user", "content": "Summarize the French Revolution in 3 lines"}],
}

response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data)
print(response.json())
