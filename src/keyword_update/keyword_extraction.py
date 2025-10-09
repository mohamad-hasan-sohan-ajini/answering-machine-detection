from sklearn.feature_extraction.text import TfidfVectorizer
from keybert import KeyBERT
import pandas as pd
import yake

vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(2, 3))
kw_extractor = yake.KeywordExtractor(lan="en", n=2, dedupLim=0.9, top=20, features=None)
kw_model = KeyBERT()

def extract_tfidf(segments):
    tfidf_matrix = vectorizer.fit_transform(segments)
    feature_names = vectorizer.get_feature_names_out()
    avg_tfidf = tfidf_matrix.mean(axis=0).A1
    df_keywords_am = pd.DataFrame({'keyword': feature_names, 'score': avg_tfidf})
    # Filter: keep only keywords with length >= 5
    df_keywords_am = df_keywords_am[df_keywords_am['keyword'].str.len() >= 5]
    # Sort and keep top 20
    df_keywords_am = df_keywords_am.sort_values(by='score', ascending=False).head(20)
    return df_keywords_am


def extract_yake(segments):
    segments = "\n".join(segments)
    keywords = kw_extractor.extract_keywords(segments)
    return keywords

def extract_keybert(segments):
    segments = "\n".join(segments)
    keywords = kw_model.extract_keywords(segments, keyphrase_ngram_range=(1, 2), stop_words='english', top_n=20)
    return keywords


def extract(segments: list):
    keywords_tfidf = extract_tfidf(segments)
    keywords_keybert = extract_keybert(segments)
    keywords_yake = extract_yake(segments)
    keywords = keywords_tfidf | keywords_keybert | keywords_yake
    return keywords

