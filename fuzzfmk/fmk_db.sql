PRAGMA foreign_keys = off;
BEGIN TRANSACTION;

CREATE TABLE CONF (
    ITEM  TEXT    PRIMARY KEY
                  UNIQUE
                  NOT NULL,
    VALUE BOOLEAN
);

CREATE TABLE PROJECT (
    NAME TEXT PRIMARY KEY
               COLLATE NOCASE
               NOT NULL
               UNIQUE ON CONFLICT IGNORE
);

CREATE TABLE DATAMODEL (
    NAME TEXT PRIMARY KEY
               COLLATE NOCASE
               NOT NULL
               UNIQUE ON CONFLICT IGNORE
);

CREATE TABLE DMAKERS (
    DM_NAME   TEXT REFERENCES DATAMODEL (NAME),
    TYPE      TEXT,
    NAME      TEXT,
    CLONE_TYPE     TEXT,
    CLONE_NAME     TEXT,
    GENERATOR  BOOLEAN,
    STATEFUL  BOOLEAN,
    PRIMARY KEY (
        TYPE,
        NAME
    ) ON CONFLICT IGNORE,
    FOREIGN KEY (
        CLONE_TYPE,
        CLONE_NAME
    )
    REFERENCES DMAKERS (TYPE,
    NAME)
);

CREATE TABLE DATA (
    ID        INTEGER  PRIMARY KEY ASC AUTOINCREMENT,
    GROUP_ID  INTEGER,
    TYPE      TEXT,
    DM_NAME   TEXT REFERENCES DATAMODEL (NAME),
    CONTENT   BLOB,
    SIZE      INTEGER,
    SENT_DATE TIMESTAMP,
    ACK_DATE  TIMESTAMP,
    TARGET TEXT,
    PRJ_NAME TEXT REFERENCES PROJECT (NAME)
);

CREATE TABLE STEPS (
    DATA_ID     INTEGER REFERENCES DATA (ID),
    STEP_ID     INTEGER,
    DMAKER_TYPE TEXT,
    DMAKER_NAME TEXT,
    DATA_ID_SRC INTEGER REFERENCES DATA (ID),
    USER_INPUT  TEXT,
    INFO        BLOB,
    PRIMARY KEY (
        DATA_ID,
        STEP_ID
    ),
    FOREIGN KEY (
        DMAKER_TYPE,
        DMAKER_NAME
    )
    REFERENCES DMAKERS (TYPE,
    NAME)
);

CREATE TABLE FEEDBACK (
    DATA_ID  INTEGER REFERENCES DATA (ID),
    SOURCE   TEXT,
    CONTENT  BLOB,
    STATUS   INTEGER,
    PRIMARY KEY (
        DATA_ID,
        SOURCE
    )
);

CREATE TABLE COMMENTS (
    ID        INTEGER  PRIMARY KEY ASC AUTOINCREMENT,
    DATA_ID   INTEGER REFERENCES DATA (ID),
    CONTENT   TEXT,
    DATE      TIMESTAMP
);

CREATE TABLE FMKINFO (
    ID        INTEGER  PRIMARY KEY ASC AUTOINCREMENT,
    DATA_ID   INTEGER REFERENCES DATA (ID),
    CONTENT   TEXT,
    DATE      TIMESTAMP,
    ERROR     BOOLEAN
);

CREATE VIEW STATS AS
    SELECT TYPE, sum(CPT) as TOTAL
    FROM (
            WITH joint AS (
                     SELECT DATA.TYPE,
                          DMAKERS.clone_type
                     FROM DATA
                          LEFT JOIN
                          DMAKERS ON DATA.TYPE = DMAKERS.TYPE
            )
            SELECT CLONE_TYPE AS type, count(*) AS cpt
            FROM joint
            WHERE CLONE_TYPE IS NOT NULL
            GROUP BY CLONE_TYPE
               UNION ALL
            SELECT TYPE, count(*) AS cpt
            FROM joint
            WHERE CLONE_TYPE IS NULL
            GROUP BY TYPE
    )
    GROUP BY TYPE;

CREATE VIEW STATS_BY_TARGET AS
  with joint as (
      select TARGET, TYPE, count(*) as CPT, CLONE_TYPE from (
          select DATA.TARGET, DATA.TYPE, DMAKERS.CLONE_TYPE
          from DATA inner join DMAKERS
              on DATA.TYPE == DMAKERS.TYPE
      )
      group by TARGET, TYPE
  )
  select TARGET, TYPE, sum(CPT) as TOTAL from (
      select TARGET, CLONE_TYPE as TYPE, CPT from joint
      where CLONE_TYPE is not null
      union all
      select TARGET, TYPE, CPT from joint
      where CLONE_TYPE is null
  )
  group by TARGET, TYPE;

COMMIT TRANSACTION;
PRAGMA foreign_keys = on;
