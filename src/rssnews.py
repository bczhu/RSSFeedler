import time
import math
import nltk
import operator
import feedparser
from html2text import html2text
from urllib.parse import urlsplit

from sklearn.feature_extraction.text import TfidfVectorizer

from db import *

FEED_DATA = []
KEYWORDS = []


# tf-idf implementation
# from http://timtrueman.com/a-quick-foray-into-linear-algebra-and-python-tf-idf/


def freq(word, document):
    """Count frequency of the word in document"""
    return document.count(word)


def word_count(document):
    """Count all words in document"""
    return len(document)


def num_docs_containing(word, documentList):
    count = 0
    for document in documentList:
        if freq(word, document) > 0:
            count += 1
    return count


def tf(word, document):
    return (freq(word, document) / float(word_count(document)))


def idf(word, documentList):
    return math.log(len(documentList) / num_docs_containing(word, documentList))


def tfidf(word, document, documentList):
    return (tf(word, document) * idf(word, documentList))


def top_keywords(n, doc, corpus):
    """Extracts the top keywords from each doc"""
    d = {}
    for word in set(doc):
        d[word] = tfidf(word, doc, corpus)
    sorted_d = sorted(d.items(), key=operator.itemgetter(1))
    sorted_d.reverse()
    return [w[0] for w in sorted_d[:n]]


def create_news(index, entry):
    """Create news"""
    return dict({
        'pk': index,
        'title': entry.get('title', ''),
        'link': entry.get('link', ''),
        'score': 0,
        'domain': entry.get('base', '')
    })


def get_saved(number_of_keywords):
    """Get saved news"""
    corpus = []
    i = 0
    global FEED_DATA
    FEED_DATA = []
    for e in get_all_saved():
        words = nltk.wordpunct_tokenize(html2text(e['description']))
        words.extend(nltk.wordpunct_tokenize(e['title']))
        lowerwords = [x.lower() for x in words if len(x) > 1]
        corpus.append(lowerwords)

        KEYWORDS.append(top_keywords(number_of_keywords, lowerwords, corpus))

        news = create_news(i, e)
        FEED_DATA.append(news)
        i += 1

    return FEED_DATA


def save(id):
    """Save or update news"""
    entry = FEED_DATA[id]
    return save_news(entry)


def delete(id):
    """Delete from saved collection"""
    entry = FEED_DATA[id]
    remove_saved(entry)


def like(id):
    """Like current news"""
    keys = KEYWORDS[id]
    create_db_post(FEED_DATA[id], keys, True)


def dislike(id):
    """Dislike current news"""
    keys = KEYWORDS[id]
    create_db_post(FEED_DATA[id], keys, False)


def get_train_data_from_db(classes):
    """Get all classified data from database"""
    train_data = []
    train_labels = []

    for entry in db.pos.find():
        content = entry['content']
        # train algorithm by words content
        train_data.append(content)
        train_labels.append('pos')

    for entry in db.neg.find():
        content = entry['content']
        # train algorithm by words content
        train_data.append(content)
        train_labels.append('neg')

    return train_data, train_labels


def get_test_data(FEED, number_of_keywords):
    """Get liked/disliked data from database"""
    test_data = []
    test_labels = []
    corpus = []
    global FEED_DATA
    FEED_DATA = []
    for f in FEED:
        d = feedparser.parse(f)
        for e in d['entries']:
            if was_read(e.get('link', '')):
                continue
            words = nltk.wordpunct_tokenize(html2text(e['description']))
            words.extend(nltk.wordpunct_tokenize(e.get('title', '')))
            lowerwords = [x.lower() for x in words if len(x) > 1]
            corpus.append(lowerwords)

            KEYWORDS.append(top_keywords(number_of_keywords, lowerwords, corpus))

            FEED_DATA.append(e)

            content = html2text(e['description'])

            test_data.append(content)
            test_labels.append('pos')
    return test_data, test_labels, d


def get_classifier(algorithm):
    """Get needed classifier"""
    classifier = None
    # Choose needed algorithm for ML
    if algorithm == "NB":
        from sklearn.naive_bayes import MultinomialNB
        classifier = MultinomialNB()
    elif algorithm == "SVC":
        from sklearn.svm import SVC
        classifier = SVC(kernel='linear', probability=True)
    elif algorithm == "TREE":
        from sklearn import tree
        classifier = tree.DecisionTreeClassifier()
    return classifier


def get_relevant_news(FEED, number_of_keywords, algorithm):
    """Get relevant news"""
    classes = ['pos', 'neg']

    train_data, train_labels = get_train_data_from_db(classes)
    test_data, test_labels, d = get_test_data(FEED, number_of_keywords)

    # Create feature vectors
    vectorizer = TfidfVectorizer(min_df=3,
                                 max_df=0.5,
                                 sublinear_tf=True,
                                 use_idf=True)
    train_vectors = vectorizer.fit_transform(train_data)
    test_vectors = vectorizer.transform(test_data)

    # Perform classification with SVM, kernel=linear
    t0 = time.time()

    classifier = get_classifier(algorithm)

    classifier.fit(train_vectors, train_labels)
    t1 = time.time()
    # prediction_linear = classifier.predict(test_vectors)

    news_list = []

    for i in range(len(test_data)):
        results = classifier.predict_proba(test_vectors)[i]
        prob_per_class = dict(zip(classifier.classes_, results))

        news = dict({
            'pk': i,
            'title': FEED_DATA[i]['title'],
            'link': FEED_DATA[i].get('link', ''),
            'score': prob_per_class['pos'],
            'domain': FEED_DATA[i].get('base', ''),
        })
        news_list.append(news)

    t2 = time.time()
    time_linear_train = t1 - t0
    time_linear_predict = t2 - t1

    print('Time train: ', time_linear_train)
    print('Time predict: ', time_linear_predict)

    return news_list


def get_domain(s):
    """Parse domain name"""
    base_url = "{0.scheme}://{0.netloc}/".format(urlsplit(s))
    return base_url.split('://')[1]


def get_feed_posts(FEED, number_of_keywords):
    """Get RSS posts from needed sources"""
    feedparser._HTMLSanitizer.acceptable_elements = (['a'])
    global FEED_DATA
    FEED_DATA = []
    corpus = []
    i = 0
    for f in FEED:
        d = feedparser.parse(f)
        for e in d['entries']:
            link = e.get('link', '')
            if was_read(link):
                continue
            words = nltk.wordpunct_tokenize(html2text(e['description']))
            words.extend(nltk.wordpunct_tokenize(e['title']))
            lowerwords = [x.lower() for x in words if len(x) > 1]
            corpus.append(lowerwords)

            KEYWORDS.append(top_keywords(number_of_keywords, lowerwords, corpus))

            news = dict({
                'pk': i,
                'title': e['title'],
                'link': link,
                'score': 0,
                'description': e['description'],
                'published': e.get('published', ''),
                'domain': get_domain(f)
            })
            FEED_DATA.append(news)
            i += 1
    return FEED_DATA


def save_current(data):
    """Save current session's news"""
    map(save_current_post, data)


def get_saved_current(per_page, count):
    """Get saved current session's news"""
    return [e for e in get_current_session(per_page, count)]
