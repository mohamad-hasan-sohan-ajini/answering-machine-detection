import re

import requests

headers = {"Content-Type": "application/json"}
url1 = "http://140.82.40.184:8000/extract_keywords"
url2 = "http://140.82.40.184:8000/check_keywords"


def extract(transcripts: list[str]) -> list[str]:
    data = {"transcripts": transcripts}
    response = requests.post(url1, json=data, headers=headers)
    data_decision = response.json()

    keywords_unchecked = []
    for keys in data_decision.values():
        if keys is not None and len(keys) > 0:
            keys = [key for key in keys if key is not None and len(key) > 5]
            keywords_unchecked.extend(keys)

    keywords_unchecked = list(set(keywords_unchecked))
    data = {"transcripts": keywords_unchecked}
    response = requests.post(url2, json=data, headers=headers)

    final_keywords = response.text
    print(f"final_keywords {final_keywords}")
    final_keywords = final_keywords.split(",")
    final_keywords = [
        re.sub(r"[^a-zA-Z' ]+", "", phrase).strip() for phrase in final_keywords
    ]
    return final_keywords
