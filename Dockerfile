FROM postgres:16

COPY ./init-scripts /docker-entrypoint-initdb.d/