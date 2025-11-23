import json
import math
import pkgutil
import re
import sys
from collections import Counter
from pathlib import Path
from time import time

import nltk
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from nltk.corpus import stopwords
from pydantic import BaseModel
from tqdm import tqdm
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

file_path = Path(__file__).resolve()
parent_dir = file_path.parent.parent
sys.path.insert(0, str(parent_dir))

from config import LLMAIAPI

times_tries_extract = LLMAIAPI.times_tries_extract
times_tries_checking = LLMAIAPI.times_tries_checking
times_double_check = LLMAIAPI.times_double_check
ignore_function_words = LLMAIAPI.ignore_function_words

nltk.download("stopwords")
ner = pipeline("ner", grouped_entities=True, device=-1)
stop_words = set(stopwords.words("english"))

tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3.1-8B-Instruct")
model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-3.1-8B-Instruct", device_map="auto", torch_dtype="auto"
)

PROMPT_EXTRACT = pkgutil.get_data("prompt", "EXTRACT_LLAMA").decode("utf-8").strip()
PROMPT_CHCECK1 = pkgutil.get_data("prompt", "CHECK_LLAMA1").decode("utf-8").strip()
PROMPT_CHCECK2 = pkgutil.get_data("prompt", "CHECK_LLAMA2").decode("utf-8").strip()
PROMPT_CHCECK = pkgutil.get_data("prompt", "CHECK_LLAMAF").decode("utf-8").strip()
PROMPT_CHCECK_list = [PROMPT_CHCECK1, PROMPT_CHCECK2]

mapping = {"False": False, "True": True, "true": True, "false": False}

app = FastAPI(
    title="Answering Machine Keyword Extractor API",
    description="Detects answering machines from call transcripts and extracts keyword n-grams.",
    version="1.0.0",
)

# Request schema
class TranscriptInput(BaseModel):
    transcripts: list[str]


def __fetch_keywords__(trans):
    messages = [
        {
            "role": "system",
            "content": (PROMPT_EXTRACT),
        },
        {
            "role": "user",
            "content": f"The transcript is:\n{trans}",
        },
    ]
    inputs = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    ).to(model.device)
    outputs = model.generate(
        **inputs, max_new_tokens=50, pad_token_id=tokenizer.eos_token_id
    )
    result = tokenizer.decode(outputs[0][inputs["input_ids"].shape[-1] :])
    keywords = []
    try:
        cleaned = re.sub(r"<\|.*?\|>", "", result).strip()
        cleaned = re.sub(r"^```[a-zA-Z0-9]*\n|```$", "", cleaned.strip())
        try:
            response = json.loads(cleaned)
        except:
            try:
                response = json.loads(cleaned + "]}")
            except:
                try:
                    response = json.loads(cleaned + '"]}')
                except:
                    response = json.loads(cleaned[:-1] + "]}")
        keyword = response.get("keywords", "")
        if keyword:
            keywords.extend(keyword)
    except:
        pass
        # breakpoint() # For debug

    return keywords


def __check_keywords__(keyword):
    inputs = tokenizer.apply_chat_template(
        keyword,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    ).to(model.device)
    outputs = model.generate(
        **inputs, max_new_tokens=40, pad_token_id=tokenizer.eos_token_id
    )
    result = tokenizer.decode(outputs[0][inputs["input_ids"].shape[-1] :])
    try:
        cleaned = re.sub(r"<\|.*?\|>", "", result).strip()
        response = re.sub(r"^```[a-zA-Z0-9]*\n|```$", "", cleaned.strip())
        status = mapping.get(response)
        if status:
            return status
    except:
        pass
        # breakpoint()

    return None


def __detect_function_words__(sentence):
    words = sentence.split()
    return [w for w in words if w.lower() in stop_words]


def extract_kw_transcripts(transcripts):
    for t in tqdm(range(times_tries_extract), desc="Extracting keywrods"):
        keywords = []
        for trans in transcripts:
            if len(trans.strip()) > 10:
                keyword = __fetch_keywords__(trans.strip())
                if keyword:
                    keywords.extend(keyword)

    keywords = list(set(keywords))
    return keywords


def check_kw_extracted(keywords):
    keywords_extracted = []
    for t in tqdm(range(times_tries_checking), desc="Checking keywrods"):
        for PROMPT_CHCECK in PROMPT_CHCECK_list:
            keywords_decision = {}
            for keyword in keywords:
                if len(keyword.strip()) > 5:
                    messages = [
                        {
                            "role": "system",
                            "content": PROMPT_CHCECK,
                        },
                        {
                            "role": "user",
                            "content": f"{keyword.strip()}",
                        },
                    ]

                    keyword_status = __check_keywords__(messages)
                    if keyword_status:
                        keywords_decision.update({keyword: keyword_status})

            keywords_extracted.extend(
                [key for key, val in keywords_decision.items() if val]
            )

    cnt = Counter(keywords_extracted)
    keywords_extracted = {
        k for k, v in cnt.items() if v > math.ceil(times_tries_checking / 2)
    }

    cleaned_keywords = []
    for key in keywords_extracted:
        if len(key.split(" ")) > 1 and len(key.split(" ")) < 4:
            key = key.strip()
            key = re.sub(r"^['\"’‘“”]|['\"’‘“”]$", "", key)
            key = key.strip()
            key = re.sub(r"^['\"’‘“”]|['\"’‘“”]$", "", key)
            if len(key) > 5 and len(key.split(" ")) > 1 and len(key.split(" ")) < 4:
                cleaned_keywords.append(key)

    cleaned_keywords = list(set(cleaned_keywords))
    return cleaned_keywords


def double_check_kw(keywords):
    filtered_keywords = []
    for key in keywords:
        if ignore_function_words:
            if not __detect_function_words__(key) and not ner(key):
                filtered_keywords.append(key.lower())
        else:
            filtered_keywords.append(key.lower())

    print(f"**** Filtered Keywords are {len(filtered_keywords)}")
    for fnum in range(times_double_check):
        keywords_decision = {}
        for keyword in tqdm(filtered_keywords, desc=f"Iteration {fnum+1}"):
            keyword = keyword.strip()
            if len(keyword) > 5:
                messages = [
                    {
                        "role": "system",
                        "content": PROMPT_CHCECK,
                    },
                    {
                        "role": "user",
                        "content": f"{keyword}",
                    },
                ]

                keyword_status = __check_keywords__(messages)
                if keyword_status:
                    keywords_decision.update({keyword: keyword_status})

        filtered_keywords = [key for key, val in keywords_decision.items() if val]

    return filtered_keywords


@app.post("/extract_keywords", response_class=JSONResponse)
def extract_keywords(data: TranscriptInput):
    keywrods = extract_kw_transcripts(data.transcripts)
    keywrods_checked = check_kw_extracted(keywrods)
    keywrods_final = double_check_kw(keywrods_checked)
    keywrods_final = [key.upper() for key in keywrods_final]
    return keywrods_final


@app.post("/check_keywords", response_class=JSONResponse)
def check_keywords(data: TranscriptInput):
    keywrods_checked = check_kw_extracted(data.transcripts)
    keywrods_final = double_check_kw(keywrods_checked)
    return keywrods_final


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "keyword_extractor_llama:app",  # module:app instance
        host="0.0.0.0",  # or "0.0.0.0" for external access
        port=8000,
        timeout_keep_alive=300,
        reload=False,  # auto-reload on code changes
    )
