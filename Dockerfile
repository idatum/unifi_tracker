from debian:bullseye-slim

RUN apt-get update

RUN apt-get install vim --yes && \
    apt-get install curl --yes && \
    apt-get install mosquitto-clients --yes && \
    apt-get install openssh-client --yes && \
    apt-get install jq --yes

RUN apt-get install python3 --yes && \
    apt-get install python3-paramiko --yes && \
    apt-get install python3-pip --yes

# https://pypi.org/project/unifi-tracker/
RUN python3 -m pip install unifi-tracker[paho-mqtt]

COPY /app /app

CMD ["/bin/sh", "/app/entrypoint.sh"]