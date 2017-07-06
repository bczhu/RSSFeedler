import time
import feedparser
from html2text import html2text
from urllib.parse import urlsplit
from collections import Counter


from nltk.tokenize import RegexpTokenizer
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer

import db

# extend standart words
stop_words = stopwords.words('russian') + stopwords.words('english')
stop_words.extend(['что', 'это', 'так', 'вот', 'быть', 'как', 'в', '—', 'к', 'на'])

FEED_DATA = []
KEYWORDS = []


def top_keywords(plain_text, number_of_keywords):
    """Extracts the top keywords from each doc"""
    plain_text = plain_text.lower()
    # tokenizer with strip punctuation
    tokenizer = RegexpTokenizer(r'\w+')
    # get base words from summary
    tokens = tokenizer.tokenize(plain_text)
    # filtering from stop words
    filtered = [w for w in tokens if (w not in stop_words)]
    count = Counter(filtered)
    # get top `number_of_keywords` words
    top_keys = [item[0] for item in count.most_common(number_of_keywords)]
    return top_keys


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
    # primary key for post
    i = 0
    global FEED_DATA
    FEED_DATA = []
    for e in db.get_all_saved():
        title = e.get('title', '')
        # try fields 'description' -> 'summary'
        summary_text = e.get('description', None) or e.get('summary', '')
        plain_text = html2text(summary_text)
        plain_text = '{} {}'.format(plain_text, title)
        top_keys = top_keywords(plain_text, number_of_keywords)
        KEYWORDS.append(top_keys)

        news = create_news(i, e)
        FEED_DATA.append(news)
        i += 1

    return FEED_DATA


def save(id):
    """Save or update news"""
    entry = FEED_DATA[id]
    return db.save_news(entry)


def delete(id):
    """Delete from saved collection"""
    entry = FEED_DATA[id]
    db.remove_saved(entry)


def like(id):
    """Like current news"""
    keys = KEYWORDS[id]
    db.create_db_post(FEED_DATA[id], keys, True)


def dislike(id):
    """Dislike current news"""
    keys = KEYWORDS[id]
    db.create_db_post(FEED_DATA[id], keys, False)


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


def get_new_data(FEED, number_of_keywords):
    """Get new data from feeds"""
    test_data = []
    test_labels = []
    global FEED_DATA
    FEED_DATA = []
    for f in FEED:
        d = feedparser.parse(f)
        for e in d['entries']:
            if db.was_read(e.get('link', '')):
                continue

            title = e.get('title', '')
            # try fields 'description' -> 'summary'
            summary_text = e.get('description', None) or e.get('summary', '')
            plain_text = html2text(summary_text)
            plain_text = '{} {}'.format(plain_text, title)
            top_keys = top_keywords(plain_text, number_of_keywords)

            # append keywords
            KEYWORDS.append(top_keys)
            # append feed entry
            FEED_DATA.append(e)

            test_data.append(' '.join(top_keys))
            # think that all posts are good
            test_labels.append('pos')
    return test_data, test_labels


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
    test_data, test_labels = get_new_data(FEED, number_of_keywords)

    print("Train data len: %s\nTest data len: %s", len(train_data), len(test_data))

    # Create feature vectors
    vectorizer = TfidfVectorizer(min_df=3,
                                 max_df=0.5,
                                 sublinear_tf=True,
                                 use_idf=True)
    # generating learning model parameters from training data then applied them
    # upon model to generate transformed data set.
    train_vectors = vectorizer.fit_transform(train_data)
    test_vectors = vectorizer.transform(test_data)

    t0 = time.time()

    # Perform classification
    classifier = get_classifier(algorithm)

    # every request train my model(!)
    # @TODO train only on change
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
    # just calculating time
    time_linear_train = t1 - t0
    time_linear_predict = t2 - t1

    print('Time train: ', time_linear_train)
    print('Time predict: ', time_linear_predict)

    return news_list


def get_domain(s):
    """Parse domain name"""
    base_url = "{0.scheme}://{0.netloc}/".format(urlsplit(s))
    return base_url.split('://')[1].replace('/', '').replace('www.', '')


def get_feed_posts(FEED, number_of_keywords):
    """Get RSS posts from needed sources"""
    feedparser._HTMLSanitizer.acceptable_elements = (['a'])
    global FEED_DATA
    FEED_DATA = []
    # primary key for post
    i = 0
    for f in FEED:
        d = feedparser.parse(f)
        for e in d['entries']:
            link = e.get('link', '')
            if db.was_read(link):
                continue
            title = e.get('title', '')
            # try fields 'description' -> 'summary'
            summary_text = e.get('description', None) or e.get('summary', '')
            plain_text = html2text(summary_text)
            plain_text = '{} {}'.format(plain_text, title)
            top_keys = top_keywords(plain_text, number_of_keywords)

            KEYWORDS.append(top_keys)

            news = dict({
                'pk': i,
                'title': e['title'],
                'link': link,
                'score': 0,
                'description': summary_text,
                'published': e.get('published', ''),
                'domain': get_domain(f)
            })
            FEED_DATA.append(news)
            i += 1
    return FEED_DATA


def save_current(data):
    """Save current session's news"""
    for item in data:
        db.save_current_post(item)


def get_saved_current(per_page, count):
    """Get saved current session's news"""
    entries = []
    for e in db.get_current_session(per_page, count):
        entries.append(e)
    return entries
