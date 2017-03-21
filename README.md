RSSFeedler
======

After Prismatic decided to shut down I wanted to get the same functionality -- I need my news back. But I didn't know about Flipboard existence. So I wrote this simple RSS aggregation tool with a bit of machine learning algorithms.

##### Dependencies

* Docker
* Docker-compose
* nginx
* uwsgi
* Flask
* feedparser
* gevent
* nltk
* numpy
* pymongo
* scikit-learn
* scipy
* sklearn

##### Installation

Create feeds.py with `FEED` list of RSS sources you interested in.

Then do:

```bash
docker-compose build
docker-compose up
```


##### Dump db

```bash
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' <container_id>
mongodump -v --host <container_ip>:27017 --db 'feed' --out=./backup/
mongodump -v --host <container_ip>:27017 --db 'saved' --out=./backup/
```


##### Restore db

```bash
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' <container_id>
mongorestore --drop -v --host <container_ip>:27017 --db 'feed' ./backup/feed/
mongorestore --drop -v --host <container_ip>:27017 --db 'saved' ./backup/feed/
```
