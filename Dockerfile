from debian:bullseye-slim

RUN apt update

RUN apt install vim --yes && \
    apt install curl --yes && \
    apt install mosquitto-clients --yes && \
    apt install openssh-client --yes && \
    apt install jq --yes

RUN apt install python3 --yes && \
    apt install python3-paho-mqtt --yes && \
    apt install python3-paramiko --yes && \
    apt install python3-pip --yes

# https://pypi.org/project/unifi-tracker/
RUN python3 -m pip install unifi-tracker

COPY /app /app

CMD ["/bin/sh", "/app/entrypoint.sh"]