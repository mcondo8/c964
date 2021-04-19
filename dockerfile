
#Base Python
FROM python:3.9.4-slim-buster

MAINTAINER Michael Condon <mcondo8@wgu.edu>

RUN apt-get update
#nginx to handle web req, supervisor to control uwsgi & nginx
#build-essential/gcc is required for uwsgi
RUN apt-get install -y nginx supervisor build-essential


#Set up venv
ENV VIRTUAL_ENV=/opt/VirtEnv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
#Get current version of pip, JIC/CYA
RUN python -m pip install -U pip
RUN pip install uwsgi
RUN echo $PATH
#Project requirements

COPY requirements.txt .
RUN pip install -r requirements.txt



