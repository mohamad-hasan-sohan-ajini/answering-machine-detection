import pandas as pd
import re

df1 = pd.read_csv("march_24_AMD.tsv", sep="\t")
full_transcript = df1["transcript"]

transcript_am = []
transcript_live = []
for line in full_transcript:
    pairs = re.findall(r'(\d+):(.*?)(?=\s*\d+:|$)', line)
    agent0_msgs = [msg.strip().strip(',') for num, msg in pairs if int(num) % 2 == 0]
    agent1_msgs = [msg.strip().strip(',') for num, msg in pairs if int(num) % 2 == 1]
    transcript_am.extend(agent0_msgs)
    # transcript_live.extend(agent1_msgs)

df1 = pd.read_csv("FEB26_amd.tsv", sep="\t")
full_transcript = df1["transcript"]

for line in full_transcript:
    pairs = re.findall(r'(\d+):(.*?)(?=\s*\d+:|$)', line)
    agent0_msgs = [msg.strip().strip(',') for num, msg in pairs if int(num) % 2 == 0]
    agent1_msgs = [msg.strip().strip(',') for num, msg in pairs if int(num) % 2 == 1]
    transcript_am.extend(agent0_msgs)
    # transcript_live.extend(agent1_msgs)


df1 = pd.read_csv("FEB26_calls.tsv", sep="\t")
full_transcript = df1["transcript"]

for line in full_transcript:
    pairs = re.findall(r'(\d+):(.*?)(?=\s*\d+:|$)', line)
    agent0_msgs = [msg.strip().strip(',') for num, msg in pairs if int(num) % 2 == 0]
    agent1_msgs = [msg.strip().strip(',') for num, msg in pairs if int(num) % 2 == 1]
    transcript_live.extend(agent0_msgs)
    # transcript_live.extend(agent1_msgs)

transcript_am = [trans_.strip() for trans_ in transcript_am if len(trans_.strip()) > 5]
transcript_live = [trans_.strip() for trans_ in transcript_live if len(trans_.strip()) > 5]
open("am", "w").write("\n".join(transcript_am))
open("live", "w").write("\n".join(transcript_live))


