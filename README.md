# answering-machine-detection
detect if the other side of a call is an answering machine


create user, database, and table:

```
sudo -i -u postgres
psql

CREATE USER auser WITH PASSWORD 'apassword';
ALTER ROLE auser WITH LOGIN;
CREATE DATABASE databasename;
GRANT ALL PRIVILEGES ON DATABASE databasename TO auser;
\c databasename;

CREATE TABLE amd_table_0 (
    call_id TEXT PRIMARY KEY,
    dialed_number TEXT,
    call_date DATE,
    call_time TIME,
    result TEXT,
    call_duration FLOAT,
    asr_result TEXT
);
GRANT ALL PRIVILEGES ON TABLE amd_table_0 TO amd_agent;
```


To manually export environment variables:

```
export $(grep -v '^#' .env | xargs)
```
