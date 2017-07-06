FROM python:3.5

ADD ./src /src
ADD requirements.txt /src
RUN pip install -r ./src/requirements.txt
RUN python -m textblob.download_corpora
RUN livereload /code &
