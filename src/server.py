# -*- coding: utf-8 -*-

from math import ceil
import gevent.monkey
from flask import Flask, render_template, jsonify, url_for, request, redirect

from rssnews import dislike, like, get_relevant_news, get_feed_posts, save, get_saved, \
    delete, save_current, get_saved_current

from db import count_current, remove_current

try:
    from feeds import FEED
except Exception as e:
    print("You need to define your feed sources in feeds.py")
    raise e

ALGORITHM = "SVC"
PER_PAGE = 20
NUMBER_OF_KEYWORDS = 30
MAX_WORDS_TITLE = 65


app = Flask(__name__, static_url_path='', static_folder='static')
gevent.monkey.patch_all()


class Pagination(object):
    def __init__(self, page, per_page, total_count):
        self.page = page
        self.per_page = per_page
        self.total_count = total_count

    @property
    def pages(self):
        return int(ceil(self.total_count / float(self.per_page)))

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.pages

    def iter_pages(self, left_edge=2, left_current=2,
                   right_current=5, right_edge=2):
        last = 0
        for num in range(1, self.pages + 1):
            if num <= left_edge or (num > self.page - left_current - 1 and num < self.page + right_current) or num > self.pages - right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num


@app.template_filter('cut')
def cut_filter(s):
    if len(s) > MAX_WORDS_TITLE:
        return "".join(s[:MAX_WORDS_TITLE]) + "..."
    return s


@app.route('/save/<id>', methods=['POST'])
def save_view(id):
    id = int(id)
    save(id)
    return jsonify({"id": id})


@app.route('/delete/<id>', methods=['POST'])
def delete_view(id):
    id = int(id)
    delete(id)
    return jsonify({"id": id})


@app.route('/like/<id>', methods=['POST'])
def like_view(id):
    id = int(id)
    like(id)
    return jsonify({"id": id})


@app.route('/dislike/<id>', methods=['POST'])
def dislike_view(id):
    id = int(id)
    dislike(id)
    return jsonify({"id": id})


@app.route('/saved')
def saved_view():
    entries_sorted = get_saved(NUMBER_OF_KEYWORDS)
    data = {
        'entries': entries_sorted,
        'count': len(entries_sorted),
        'view_name': 'saved',
    }
    return render_template('index.html', **data)


@app.route('/relevant/update')
def update_relevant():
    """Updates relevant feeds"""
    print("Update relevant!")
    remove_current()
    entries_sorted = get_relevant_news(FEED, NUMBER_OF_KEYWORDS, ALGORITHM)
    entries_sorted = sorted(entries_sorted, key=lambda e: e['score'], reverse=True)
    save_current(entries_sorted)
    return redirect('/relevant')


@app.route('/relevant', defaults={'page': 1})
@app.route('/relevant/page/<int:page>')
def index_relevant(page):
    print("ML is ON!")
    entries_sorted = get_saved_current(PER_PAGE, page)
    if not entries_sorted:
        entries_sorted = get_relevant_news(FEED, NUMBER_OF_KEYWORDS, ALGORITHM)
        entries_sorted = sorted(entries_sorted, key=lambda e: e['score'], reverse=True)
        save_current(entries_sorted)
        entries_sorted = entries_sorted[PER_PAGE * (page - 1): PER_PAGE * page]

    count = count_current() or len(entries_sorted)
    data = {
        'entries': entries_sorted,
        'count': count,
        'view_name': 'relevant',
    }
    pagination = Pagination(page, PER_PAGE, count)
    return render_template('index.html', pagination=pagination, **data)


@app.route('/update')
def update_newest():
    """Updates newest feeds"""
    print("Update newest!")
    remove_current()
    entries_sorted = get_feed_posts(FEED, NUMBER_OF_KEYWORDS)
    entries_sorted = sorted(entries_sorted, key=lambda e: e['published'], reverse=True)
    save_current(entries_sorted)
    return redirect('/')


@app.route('/', defaults={'page': 1})
@app.route('/page/<int:page>')
def index(page):
    print("Without ML!")
    entries_sorted = get_saved_current(PER_PAGE, page)
    if not entries_sorted:
        entries_sorted = get_feed_posts(FEED, NUMBER_OF_KEYWORDS)
        save_current(entries_sorted)
        entries_sorted = entries_sorted[PER_PAGE * (page - 1): PER_PAGE * page]

    count = count_current() or len(entries_sorted)

    data = {
        'entries': entries_sorted,
        'count': count,
        'view_name': 'index',
    }
    pagination = Pagination(page, PER_PAGE, count)
    return render_template('index.html', pagination=pagination, **data)


def url_for_other_page(page):
    args = request.view_args.copy()
    args['page'] = page
    return url_for(request.endpoint, **args)
app.jinja_env.globals['url_for_other_page'] = url_for_other_page


if __name__ == '__main__':
    app.run(host='0.0.0.0', threaded=True)
