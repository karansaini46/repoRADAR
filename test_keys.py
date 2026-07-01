import os
import asyncio
from google import genai
from dotenv import load_dotenv

load_dotenv()
api_keys_str = os.getenv("GEMINI_API_KEYS", "")
keys = [k.strip() for k in api_keys_str.split(",") if k.strip()]

async def test_key(key):
    try:
        client = genai.Client(api_key=key)
        response = await client.aio.models.generate_content(
            model='gemini-2.5-flash',
            contents='Hello'
        )
        return True, None
    except Exception as e:
        return False, str(e)

async def main():
    tasks = [test_key(key) for key in keys]
    results = await asyncio.gather(*tasks)
    errors = 0
    for i, (success, err) in enumerate(results):
        if not success:
            print(f"Key {i+1} failed: {err}")
            errors += 1
    print(f"Total keys with errors: {errors} out of {len(keys)}")

if __name__ == "__main__":
    asyncio.run(main())
