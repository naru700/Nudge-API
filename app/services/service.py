from openai import OpenAI, AsyncOpenAI, RateLimitError, OpenAIError
from app.core.config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)
async_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

def get_llm_response(messages: list[dict], model: str) -> str:
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages
        )
        return response.choices[0].message.content.strip()
    except RateLimitError:
        return "[ERROR] Rate limit exceeded."
    except OpenAIError:
        return "[ERROR] LLM error occurred."

async def stream_llm_response(messages: list[dict], model: str):
    """Async generator yielding raw token strings from OpenAI streaming API."""
    stream = await async_client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True
    )
    async for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
