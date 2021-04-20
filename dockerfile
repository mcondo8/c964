
#Base Python
FROM python:3.9.4-slim-buster

MAINTAINER Michael Condon <mcondo8@wgu.edu>

WORKDIR /

RUN apt-get update
#nginx to handle web req, supervisor to control uwsgi & nginx
#build-essential/gcc is required for uwsgi

#Set up venv
# ENV VIRTUAL_ENV=/opt/VirtEnv
# RUN python3 -m venv $VIRTUAL_ENV
# ENV PATH="$VIRTUAL_ENV/bin:$PATH"
#Get current version of pip, JIC/CYA
# RUN echo $PATH

#Project requirements
COPY requirements.txt .
COPY /app /app
RUN mkdir /app/uploads
RUN pip install -r requirements.txt
ENTRYPOINT ["python"]
CMD ["app/app.py"]



