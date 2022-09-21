FROM ubuntu:22.04

RUN apt-get update
RUN apt-get install npm -y


COPY pty-server /opt/pty-server

WORKDIR /opt/pty-server
RUN npm install

CMD ["npm", "run", "start"]