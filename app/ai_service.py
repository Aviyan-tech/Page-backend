import os

import httpx

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"

def fallback_summary(content: str) -> str:
    """
    Fallback method to summarize content by truncating it to 100 characters.
    """
    clean_content = content.strip()
    if len(clean_content) <= 100:
        return clean_content
    return clean_content[:100].rstrip() + "..."

async def generate_ai_summary(content: str) -> str:
    """
    Sends the post's content to Groq's API (model: llama-3.1-8b-instant)
    and generates a one-sentence AI summary.
    
    If the API call fails (or the API key is not configured), it falls back
    to content truncation so that the application never crashes.
    """
    # Avoid calling the API if no valid key is set (e.g., example/placeholder values)
    if not GROQ_API_KEY or GROQ_API_KEY.strip() == "" or "your_" in GROQ_API_KEY:
        return fallback_summary(content)

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant. Summarize the following news article content in exactly one sentence."
            },
            {
                "role": "user",
                "content": content
            }
        ],
        "temperature": 0.3,
        "max_tokens": 150
    }

    try:
        # Using AsyncClient with a 10-second timeout
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(GROQ_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            response_data = response.json()
            ai_text = response_data["choices"][0]["message"]["content"].strip()
            # Clean up leading/trailing double quotes if returned by the model
            if ai_text.startswith('"') and ai_text.endswith('"'):
                ai_text = ai_text[1:-1].strip()
            return ai_text
    except Exception as e:
        # Fallback to truncation on any network error, API error, or timeout
        print(f"[AI Service] Groq API call failed: {e}. Falling back to content truncation.")
        return fallback_summary(content)
