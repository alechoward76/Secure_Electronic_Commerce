
-- create table ccinfo (saltpan INT, pan BLOB, saltcvv INT, cvv BLOB, expmonth INT, expyear INT, billzip INT);

DROP TABLE IF EXISTS `ccinfo`;
DROP TABLE IF EXISTS `auth`;

CREATE TABLE ccinfo (
    ivpan BLOB,
    pan BLOB,
    ivcvv BLOB,
    cvv BLOB,
    expmonth INT,
    expyear INT,
    billzip INT,
    customer VARCHAR(40),
    primary key (expmonth,expyear,billzip,customer)
);

CREATE TABLE auth (
    trans_id INT NOT NULL AUTO_INCREMENT,
    tpan BLOB,
    cvv BLOB,
    exp_date VARCHAR(255),
    amount VARCHAR(255),
    name VARCHAR(255),
    billzip INT,
    merchant VARCHAR(255),
    timestamp DATETIME,
    authorization VARCHAR(24),
    primary key (trans_id)
);
