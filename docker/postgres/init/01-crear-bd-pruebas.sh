#!/bin/sh
# Crea la base de datos de pruebas junto a la de desarrollo.
# Solo se ejecuta la primera vez que se crea el volumen de PostgreSQL.
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE ${POSTGRES_DB}_test OWNER $POSTGRES_USER;
EOSQL
