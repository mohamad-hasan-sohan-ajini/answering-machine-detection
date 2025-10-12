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
CREATE ROLE amd_agent WITH LOGIN PASSWORD 'amd_agent_password';
GRANT ALL PRIVILEGES ON TABLE amd_table_0 TO amd_agent;
```


To manually export environment variables:

```
export $(grep -v '^#' .env | xargs)
```

## Handle possible errors
If this error is seen in asterisk:\n
"radcli: rc_avpair_new: rc_avpair_new: no attribute 22736/101 in dictionary"\n
add these lines to "/etc/asterisk/modules.conf"
```bash
noload => cdr_radius.so
noload => cel_radius.so
```

## Test files (more than projects service)
### Keyword Extraction
For accurate Keyword extraction using openAI APIs, put both am and live files in the path (test), then run `python extract_keywords_am.py`, it may takes time based on the number of utterances. Then, run `python check_keywords_am.py` to double check the large extracted keywords and filter doubtful keywords. The reulting files of these two runs are equivalently "keywords.txt" for all extracted keywords and "keywords_checked.txt" for double checked keywords.

