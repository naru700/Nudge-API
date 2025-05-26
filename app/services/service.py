from openai import OpenAI, RateLimitError, OpenAIError
from app.core.config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

def get_llm_response(messages: list[dict]) -> str:
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages
        )
        return response.choices[0].message.content.strip()
    except RateLimitError:
        return "[ERROR] Rate limit exceeded."
    except OpenAIError:
        return "[ERROR] LLM error occurred."
