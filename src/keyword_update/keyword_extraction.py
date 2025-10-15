import yake
from keybert import KeyBERT
from sklearn.feature_extraction.text import TfidfVectorizer

vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(2, 3))
kw_extractor = yake.KeywordExtractor(lan="en", n=2, dedupLim=0.9, top=20, features=None)
kw_model = KeyBERT()


def extract_tfidf(segments):
    tfidf_matrix = vectorizer.fit_transform(segments)
    feature_names = vectorizer.get_feature_names_out()
    avg_tfidf = tfidf_matrix.mean(axis=0).A1
    keywords_dict = {feature_names[i]: avg_tfidf[i] for i in range(len(feature_names))}
    filtered_dict = {k: v for k, v in keywords_dict.items() if len(k) >= 5}
    sorted_items = sorted(filtered_dict.items(), key=lambda x: x[1], reverse=True)[:20]
    keywords = dict(sorted_items)
    return keywords


def extract_yake(segments):
    segments = "\n".join(segments)
    keywords = kw_extractor.extract_keywords(segments)
    keywords = dict(keywords)
    return keywords


def extract_keybert(segments):
    segments = "\n".join(segments)
    keywords = kw_model.extract_keywords(
        segments, keyphrase_ngram_range=(2, 3), stop_words="english", top_n=20
    )
    keywords = dict(keywords)
    return keywords


def extract(segments: list):
    keywords_tfidf = extract_tfidf(segments)
    keywords_keybert = extract_keybert(segments)
    keywords_yake = extract_yake(segments)
    keywords = keywords_tfidf | keywords_keybert | keywords_yake
    return keywords
