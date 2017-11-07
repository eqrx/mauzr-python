FROM python:3

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

LABEL \
org.label-schema.schema-version=1.0 \
org.label-schema.name=mauzr \
org.label-schema.vcs-url=https://github.com/eqrx/mauzr \
org.label-schema.vcs-ref=$VCS_REF \
org.label-schema.version=$VERSION \
net.eqrx.mauzr.version=$VERSION \
net.eqrx.mauzr.vcs-ref=$VCS_REF

RUN pip3 install -U --no-cache-dir mauzr[esp]==$VERSION
