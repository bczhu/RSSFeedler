import os
import pymongo
import hashlib

DEBUG = True

client = pymongo.MongoClient()
if DEBUG:
    client = pymongo.MongoClient('localhost', 27017)
else:
    client = pymongo.MongoClient(os.environ['DB_PORT_27017_TCP_ADDR'], 27017)

db = client['feed']

pos = db.pos
neg = db.neg
saved = db.saved
current = db.saved_current


def get_hash(link):
    return hashlib.sha256(link.encode('utf-8')).hexdigest()


def remove_saved(entry):
    saved.remove({'hash': get_hash(entry['link'])})


def save_news(entry):
    """Saves news in database"""
    h = get_hash(entry['link'])
    return saved.update(
        {'hash': h},
        {
            'link': entry['link'],
            'title': entry['title'],
            'description': entry['description'],
            'domain': entry.get('base', ''),
            'hash': h
        }, upsert=True
    )


def get_all_saved():
    return saved.find()


def create_db_post(entry, keys, like):
    """Creates or updates news in database on like and dislike"""
    h = get_hash(entry['link'])
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


def save_current_post(entry):
    """Save one current session news"""
    return current.insert_one(entry).inserted_id


def was_read(link):
    """Identifies if news was already read"""
    return neg.find_one({'hash': get_hash(link)}) or pos.find_one({'hash': get_hash(link)}) \
        or saved.find_one({'hash': get_hash(link)})


def get_current_session(per_page, count):
    """Gets all news from current session"""
    return current.find().sort("published", pymongo.DESCENDING).sort("score", pymongo.DESCENDING)[per_page * (count - 1):per_page * count]


def remove_current():
    """Remove current session news"""
    current.remove()


def count_current():
    """Count current session news"""
    return current.count()
