FROM docker.io/alpine:3.17.1
ENV TINI_VERSION v0.19.0
ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini /tini
RUN chmod +x /tini \
    && mkdir /opt/glowbot \
    && adduser -u 1000 -D -h /opt/glowbot glowbot \
    && chown glowbot:glowbot /opt/glowbot \
    && apk add \
        git \
        curl \
        python3
USER glowbot
WORKDIR /opt/glowbot
ADD . .
ENTRYPOINT ["/tini", "--"]
CMD ["glowbot"]