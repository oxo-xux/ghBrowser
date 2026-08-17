FROM lscr.io/linuxserver/webtop:alpine-xfce

LABEL org.opencontainers.image.source="https://github.com/oxo-xux/ghBrowser"

ENV PUID=1000
ENV PGID=1000
ENV TZ=Etc/UTC
