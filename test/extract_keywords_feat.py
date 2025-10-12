# feature based keyword extractore
from keybert import KeyBERT
import yake

segments = open("/home/navid/am").read().strip()

kw_extractor = yake.KeywordExtractor(lan="en", n=2, dedupLim=0.9, top=20, features=None)

print("ooooo AM ooooo")
print("\nYake")
keywords = kw_extractor.extract_keywords(segments)
for kw, score in keywords:
    print(f"{kw} (score: {score:.4f})")

kw_model = KeyBERT()
keywords = kw_model.extract_keywords(segments, keyphrase_ngram_range=(1, 2), stop_words='english', top_n=20)

print("\nKeyBert")
for kw, score in keywords:
    print(f"{kw} (score: {score:.4f})")

print("ooooo LIVE ooooo")

segments = open("/home/navid/live").read().strip()

kw_extractor = yake.KeywordExtractor(lan="en", n=2, dedupLim=0.9, top=20, features=None)

print("\nYake")
keywords = kw_extractor.extract_keywords(segments)
for kw, score in keywords:
    print(f"{kw} (score: {score:.4f})")

print("\nKeyBert")
kw_model = KeyBERT()
keywords = kw_model.extract_keywords(segments, keyphrase_ngram_range=(1, 2), stop_words='english', top_n=20)

for kw, score in keywords:
    print(f"{kw} (score: {score:.4f})")




