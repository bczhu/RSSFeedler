RSSFeedler
======

After Prismatic decided to shut down I wanted to get the same functionality -- I need my news back. But I didn't know about Flipboard existence. So I wrote this simple RSS aggregation tool with a bit of machine learning algorithms.

I'm a busy man but in the same time I want to know all news I am interested in. To save a bit of time I started this project. In it I try to teach my news aggregator what news I like and what I dislike by extracting top keywords from feed entry and based on previously liked posts classify new news =). As a result classification is based on user preference and sorts by 'scores'.

You can choose ML algorithm for classification in `server.py` from Naive Bayes, Support Vector Machine and Decision Tree. Default is Support Vector Machine because for me it works better.

On start relevant link will fall with 500 error because there will be not enough information of you likes/dislikes. You need at first read news from main feed which sorted by published time.

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
mongodump -v --host $(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $(docker ps -q --filter "name=rssnews_db_1")):27017 --db 'feed' --out=./backup/
mongodump -v --host $(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $(docker ps -q --filter "name=rssnews_db_1")):27017 --db 'saved' --out=./backup/
```


##### Restore db

```bash
mongorestore --drop -v --host $(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $(docker ps -q --filter "name=rssnews_db_1")):27017 --db 'feed' ./backup/feed/
mongorestore --drop -v --host $(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $(docker ps -q --filter "name=rssnews_db_1")):27017 --db 'saved' ./backup/feed/
```
 #### Todo
 
 - News by source tab
 - SPA 
 - Store algorithm in db 
 
