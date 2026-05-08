from os import getenv
from dotenv import load_dotenv
from groq import AsyncGroq

load_dotenv()

openai_client = AsyncGroq(
    api_key=getenv("GROQ_API_KEY")
)
