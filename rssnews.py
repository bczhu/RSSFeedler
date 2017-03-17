import os
import time
import math
import nltk
import hashlib
import pymongo
import operator
import feedparser
from html2text import html2text
from gevent.pool import Pool

from sklearn.svm import SVC
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB

NUMBER_OF_KEYWORDS = 30
FEED_DATA = []
KEYWORDS = []
client = pymongo.MongoClient()
client = pymongo.MongoClient('localhost', 27017)
db = client['feed']
pos = db.pos
neg = db.neg

# tf-idf implementation
# from http://timtrueman.com/a-quick-foray-into-linear-algebra-and-python-tf-idf/


def freq(word, document):
    return document.count(word)


def wordCount(document):
    return len(document)


def numDocsContaining(word, documentList):
    count = 0
    for document in documentList:
        if freq(word, document) > 0:
            count += 1
    return count


def tf(word, document):
    return (freq(word, document) / float(wordCount(document)))


def idf(word, documentList):
    return math.log(len(documentList) / numDocsContaining(word, documentList))


def tfidf(word, document, documentList):
    return (tf(word, document) * idf(word, documentList))


# KEYWORDS EXTRACTION
# extracts the top keywords from each doc
# This defines features of a common feature vector
def top_keywords(n, doc, corpus):
    d = {}
    for word in set(doc):
        d[word] = tfidf(word, doc, corpus)
    sorted_d = sorted(d.items(), key=operator.itemgetter(1))
    sorted_d.reverse()
    return [w[0] for w in sorted_d[:n]]


def create_news(i, e):
    return dict({'pk': i, 'title': e['title'], 'link': e['link'], 'score': 0})


def get_saved():
    corpus = []
    i = 0
    FEED_DATA = []
    for e in db.saved.find():
        words = nltk.wordpunct_tokenize(html2text(e['description']))
        words.extend(nltk.wordpunct_tokenize(e['title']))
        lowerwords = [x.lower() for x in words if len(x) > 1]
        corpus.append(lowerwords)

        KEYWORDS.append(top_keywords(NUMBER_OF_KEYWORDS, lowerwords, corpus))

        news = create_news(i, e)
        FEED_DATA.append(news)
        i += 1
    return FEED_DATA


def save(id):
    entry = FEED_DATA[id]
    h = hashlib.sha256(entry['link'].encode('utf-8')).hexdigest()
    return db.saved.update(
        {'hash': h},
        {
            'link': entry['link'],
            'title': entry['title'],
            'description': entry['description'],
            'hash': h
        }, upsert=True
    )


def delete(id):
    print(FEED_DATA)
    entry = FEED_DATA[id]
    h = hashlib.sha256(entry['link'].encode('utf-8')).hexdigest()
    db.saved.remove({'hash': h})


def like(id):
    keys = KEYWORDS[id]
    create_db_post(FEED_DATA[id], keys, True)


def dislike(id):
    keys = KEYWORDS[id]
    create_db_post(FEED_DATA[id], keys, False)


def create_db_post(entry, keys, like):
    h = hashlib.sha256(entry['link'].encode('utf-8')).hexdigest()
    collection = pos if like else neg
    return collection.update(
        {'hash': h},
        {
            'link': entry['link'],
            'title': entry['title'],
            'published': '',
            'content': " ".join(keys),
            'hash': h,
            'read': False
        }, upsert=True
    )


def get_train_data_from_db(classes):
    train_data = []
    train_labels = []

    for entry in db.pos.find():
        print(entry['content'].encode('utf8'))
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


def get_test_data(FEED):
    test_data = []
    test_labels = []
    corpus = []
    global FEED_DATA
    FEED_DATA = []
    for f in FEED:
        d = feedparser.parse(f)
        for e in d['entries']:
            if db.neg.find_one({'hash': hashlib.sha256(e['link'].encode('utf-8')).hexdigest()}) \
                    or db.pos.find_one({'hash': hashlib.sha256(e['link'].encode('utf-8')).hexdigest()}):
                continue
            words = nltk.wordpunct_tokenize(html2text(e['description']))
            words.extend(nltk.wordpunct_tokenize(e['title']))
            lowerwords = [x.lower() for x in words if len(x) > 1]
            corpus.append(lowerwords)

            KEYWORDS.append(top_keywords(NUMBER_OF_KEYWORDS, lowerwords, corpus))

            FEED_DATA.append(e)
            print(e['title'].encode('utf-8'))

            content = html2text(e['description'])

            test_data.append(content)
            test_labels.append('neg')
    return test_data, test_labels, d


def add_news():
    pass


def process(FEED):
    classes = ['pos', 'neg']

    # Read the data
    train_data, train_labels = get_train_data_from_db(classes)
    test_data, test_labels, d = get_test_data(FEED)

    # Create feature vectors
    vectorizer = TfidfVectorizer(min_df=3,
                                 max_df=0.5,
                                 sublinear_tf=True,
                                 use_idf=True)
    train_vectors = vectorizer.fit_transform(train_data)
    test_vectors = vectorizer.transform(test_data)
    print("Overall length: {}".format(len(test_data)))

    # Perform classification with SVM, kernel=linear
    # classifier_linear = svm.SVC(kernel='linear', probability=True)
    # MultinomialNB
    classifier_linear = MultinomialNB()
    t0 = time.time()

    classifier_linear.fit(train_vectors, train_labels)
    t1 = time.time()
    prediction_linear = classifier_linear.predict(test_vectors)
    print(prediction_linear)

    news_list = []

    for i in range(len(test_data)):
        results = classifier_linear.predict_proba(test_vectors)[i]
        prob_per_class_dictionary = dict(zip(classifier_linear.classes_, results))
        print(prob_per_class_dictionary)

        news = dict({'pk': i, 'title': FEED_DATA[i]['title'], 'link': FEED_DATA[i]['link'], 'score': prob_per_class_dictionary['pos']})
        news_list.append(news)

    t2 = time.time()
    time_linear_train = t1 - t0
    time_linear_predict = t2 - t1

    print('Time train: ', time_linear_train)
    print('Time predict: ', time_linear_predict)

    return news_list


def fetch_feeds(urls):
    pool = Pool(10)
    feedparser._HTMLSanitizer.acceptable_elements = (['a'])  # We don't want anything else
    entries = []

    def get(url):
        parsed = feedparser.parse(url)
        if parsed.entries:
            entries.extend(parsed.entries)

    for url in urls:
        pool.spawn(get, url)
    pool.join()

    return entries


def get_feed_posts(FEED):
    global FEED_DATA
    FEED_DATA = []
    corpus = []
    i = 0
    for f in FEED:
        d = feedparser.parse(f)
        for e in d['entries']:
            if db.neg.find_one({'hash': hashlib.sha256(e['link'].encode('utf-8')).hexdigest()}) \
                    or db.pos.find_one({'hash': hashlib.sha256(e['link'].encode('utf-8')).hexdigest()}):
                continue
            words = nltk.wordpunct_tokenize(html2text(e['description']))
            words.extend(nltk.wordpunct_tokenize(e['title']))
            lowerwords = [x.lower() for x in words if len(x) > 1]
            corpus.append(lowerwords)

            KEYWORDS.append(top_keywords(NUMBER_OF_KEYWORDS, lowerwords, corpus))

            news = dict({'pk': i, 'title': e['title'], 'link': e['link'], 'score': 0, 'description': e['description']})
            FEED_DATA.append(news)
            i += 1
    return FEED_DATA
