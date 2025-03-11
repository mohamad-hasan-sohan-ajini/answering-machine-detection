# answering-machine-detection
detect if the other side of a call is an answering machine


create user, database, and table:

```
sudo -i -u postgres
psql

CREATE USER auser WITH ENCRYPTED PASSWORD 'apassword';
ALTER ROLE auser WITH LOGIN;
GRANT ALL PRIVILEGES ON DATABASE mydatabase TO auser;

CREATE DATABASE databasename;
GRANT ALL PRIVILEGES ON DATABASE databasename TO auser;

CREATE TABLE amd_table_0 (
    call_id TEXT PRIMARY KEY,
    dialed_number TEXT,
    call_date DATE,
    call_time TIME,
    result_in_text TEXT,
    call_duration FLOAT,
    asr_result_in_text TEXT
);
```
