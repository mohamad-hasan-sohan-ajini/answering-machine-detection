import json
import math

from openai import OpenAI

client = OpenAI(api_key=API_KEY)

PROMPT = "You are a call record checker for detecting ansering machines, you are given a list of transcripts each in a line and you should first decide which one is an answeing machone behind it and extract 2-3 grams keywords for detecting answering machine. Return response only in json format with line numbers from 0 as key without extra explanation"


def cpr_from_title(transcripts: str):
    print(transcripts)
    resp = client.responses.create(
        model="gpt-5-nano",  # choose your model
        input=[
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": transcripts},
        ],
    )
    cpr = json.loads(resp.output_text)
    print(cpr)

    return cpr


transcripts1 = open("am").read().strip()
transcripts2 = open("live").read().strip()
transcripts = transcripts1 + "\n" + transcripts2
transcripts = transcripts.split("\n")
transcripts = list(set(transcripts))
keywords = []
processed = []
for sec_ in range(math.ceil(len(transcripts) / 20)):
    try:
        response = cpr_from_title("\n".join(transcripts[sec_ * 20 : (sec_ + 1) * 20]))
        processed.extend(transcripts[sec_ * 20 : (sec_ + 1) * 20])
    except:
        continue
    keywords.append(json.dumps(response))
    open("temp_keyword_dumper.txt", "a").write(
        "\n".join(transcripts[sec_ * 20 : (sec_ + 1) * 20]) + "\n" + response + "\n"
    )

open("transcripts.txt", "w").write("\n".join(processed))
open("keywords.txt", "w").write("\n".join(keywords))
