import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
r = client.models.generate_content(
    model="gemini-3.6-flash",
    contents="Reply with exactly: Gemini OK",
)
print(r.text)