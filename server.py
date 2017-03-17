# -*- coding: utf-8 -*-
import os
import time
import gevent.monkey

from flask import Flask, render_template, jsonify

from rssnews import dislike, like, process, get_feed_posts, save, get_saved, delete


try:
    from feeds import FEED
except Exception as e:
    print("You need to define your feed sources in feeds.py")
    raise e

app = Flask(__name__, static_url_path='', static_folder='')
gevent.monkey.patch_all()

update_time_sec = 60 * 5  # 5 min
tmp_file = "{0}/cache.tmp".format(os.path.dirname(os.path.realpath(__file__)))

if not os.path.isfile(tmp_file):
    os.mknod(tmp_file)


def update_cache(tmp_file, cache):
    with open(tmp_file, 'w') as file:
        file.write(str(cache))


def return_cache(tmp_file, update_time_sec):
    if os.path.getctime(tmp_file) < (time.time() - update_time_sec):
        with open(tmp_file, "r") as data:
                return data
    return None


@app.route('/read')
def read():
    pass


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
    entries_sorted = get_saved()
    data = {
        'top': entries_sorted[:10],
        'entries': entries_sorted[10:],
        'count': len(entries_sorted),
        'view_name': 'saved',
    }
    return render_template('index.html', **data)


@app.route('/relevant')
def index_relevant():
    FEED_DATA = []
    entries_sorted = None  # return_cache(tmp_file, update_time_sec)

    if entries_sorted is not None:
        return render_template('index.html', entries=entries_sorted)
    else:
        # try:
        entries_sorted = process(FEED)
        entries_sorted = sorted(entries_sorted, key=lambda e: e['score'], reverse=True)
        # except Exception as e:
        #     print(e)
        #     entries_sorted = []
        # update_cache(tmp_file, entries_sorted)
        data = {
            'top': entries_sorted[:10],
            'entries': entries_sorted[10:],
            'count': len(entries_sorted),
            'view_name': 'relevant',
        }
        return render_template('index.html', **data)


@app.route('/')
def index():
    FEED_DATA = []
    print("Without ML!")
    entries_sorted = get_feed_posts(FEED)
    data = {
        'top': entries_sorted[:10],
        'entries': entries_sorted[10:],
        'count': len(entries_sorted),
        'view_name': 'index',
    }
    return render_template('index.html', **data)

if __name__ == '__main__':
    app.run(host='0.0.0.0')
