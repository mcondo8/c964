
#Base Python
FROM python:3.9.4-slim-buster

MAINTAINER Michael Condon <mcondo8@wgu.edu>

WORKDIR /

RUN apt-get update
#nginx to handle web req, supervisor to control uwsgi & nginx
#build-essential/gcc is required for uwsgi

#Set up venv
ENV VIRTUAL_ENV=/app/VirtEnv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

#Project requirements, installed in virtual environment
COPY requirements.txt .
COPY /app /app
RUN mkdir /app/uploads
RUN pip install -r requirements.txt
#The following are required for opencv to function
#	Default opencv package does not include these two requirements
RUN apt-get install -y libgl1-mesa-glx
RUN apt-get install -y libglib2.0-0
#Entrypoint at app launch
ENTRYPOINT ["python"]
CMD ["app/script_api.py"]



