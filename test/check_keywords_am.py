from openai import OpenAI
import json
import math

client = OpenAI(api_key=API_KEY)

PROMPT = "I’m building a keyword detector to separate answering machines from live callers. Given a comma-separated keyword list, keep only unambiguous keywords that indicate an answering machine. Discard any terms commonly used by live callers at the start of a call."

import ast
import json
import pandas as pd

lines = open("temp_keyword_dumper.txt").read().strip().split("\n")

results = ["transcript|am|Keywords"]
transcripts = []
for line in lines:
    if line.startswith("{"):
        data = ast.literal_eval(line.strip())
        transcripts = transcripts[-len(data):]
        for k, transcript in enumerate(transcripts):
            if str(k) not in data.keys():
                continue
            gpt = data[str(k)]
            if type(gpt) is dict:
                for key in gpt.keys():
                    if key.startswith("is") or "machine" in key:
                        flag = gpt.get(key)
                        break
                else:
                    flag = ""
                if flag != False and "keywords" not in gpt:
                    breakpoint()
                results.append(transcript + "|" + str(flag) + "|" + " ; ".join(gpt.get("keywords", "")))
            else:
                results.append(transcript + "||" + " ; ".join(gpt))
        transcripts = []
    else:
        transcripts.append(line.strip())

open("gpt_results.csv", "w").write("\n".join(results))

tl = pd.read_csv("gpt_results.csv", delimiter="|")
keywords= tl["Keywords"]
full_keys = [str(item) for item in keywords if str(item) != 'nan']
full_keys = list(set(full_keys))
open("optional_keywords.txt", "w").write(",".join(full_keys))



def cpr_from_title(transcripts: str):
    print(transcripts)
    resp = client.responses.create(
        model="gpt-5-nano",  # choose your model
        input=[
            {"role":"system","content": PROMPT},
            {"role":"user","content": transcripts}
        ]
    )
    cpr = resp.output_text
    print(cpr)

    return cpr

transcripts = open("optional_keywords.txt").read().strip()

response = cpr_from_title(transcripts)
open("keywords_checked.txt", "w").write(response)


