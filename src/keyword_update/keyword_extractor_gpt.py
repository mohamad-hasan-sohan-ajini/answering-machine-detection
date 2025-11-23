import json
import os
import pkgutil
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from openai import OpenAI
from pydantic import BaseModel

file_path = Path(__file__).resolve()
parent_dir = file_path.parent.parent
sys.path.insert(0, str(parent_dir))

from config import OpenAIAPI

# Initialize OpenAI client
client = OpenAI(api_key=OpenAIAPI.apikey)

# FastAPI app initialization
app = FastAPI(
    title="Answering Machine Keyword Extractor API",
    description="Detects answering machines from call transcripts and extracts keyword n-grams.",
    version="1.0.0",
)

# Request schema
class TranscriptInput(BaseModel):
    transcripts: list[str]


# Response schema
# class KeywordResponse(BaseModel):
#     keywords: dict[int, list[str]]

PROMPT_EXTRACT = pkgutil.get_data("prompt", "EXTRACT_GPT").decode("utf-8").strip()
PROMPT_CHECK = pkgutil.get_data("prompt", "CHECK_GPT").decode("utf-8").strip()


def analyze_transcripts(transcripts: list[str]) -> dict[int, list[str]]:
    keywords_result = {}

    for batch_index in range(0, len(transcripts), 20)):
        segment = transcripts[batch_index: batch_index+20]
        try:
            resp = client.responses.create(
                model=OpenAIAPI.model,
                input=[
                    {"role": "system", "content": PROMPT_EXTRACT},
                    {"role": "user", "content": "\n".join(segment)},
                ],
            )

            parsed = json.loads(resp.output_text)
            keywords_result.update(parsed)
        except Exception as e:
            print(f"Error in batch {batch_index}: {e}")
            continue

    return keywords_result


def analyze_keywords(transcripts: list[str]) -> str:
    keywords_result = []

    for batch_index in range(0, len(transcripts), 20):
        segment = transcripts[batch_index: batch_index+20]
        try:
            resp = client.responses.create(
                model=OpenAIAPI.model,
                input=[
                    {"role": "system", "content": PROMPT_CHECK},
                    {"role": "user", "content": ",".join(segment)},
                ],
            )

            cpr = resp.output_text
            keywords_result.append(cpr)
        except Exception as e:
            print(f"Error in batch {batch_index}: {e}")
            continue

    return ",".join(keywords_result)


@app.post(
    "/extract_keywords", response_class=JSONResponse
)  # response_model=KeywordResponse
def extract_keywords(data: TranscriptInput):
    result = analyze_transcripts(data.transcripts)
    return result


@app.post(
    "/check_keywords", response_class=JSONResponse
)  # response_model=KeywordResponse
def check_keywords(data: TranscriptInput):
    result = analyze_keywords(data.transcripts)
    return result


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "keyword_extractor_gpt:app",  # module:app instance
        host="127.0.0.1",  # or "0.0.0.0" for external access
        port=8000,
        reload=True,  # auto-reload on code changes
    )
