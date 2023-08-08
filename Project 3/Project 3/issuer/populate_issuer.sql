#db 
CREATE database ccissuer;
USE ccissuer;
GRANT ALL PRIVILEGES ON ccissuer.* To 'issuer'@'localhost' IDENTIFIED BY 'HamsterEMV';

create table ccinfo (saltpan INT, pan BLOB, saltcvv INT, cvv BLOB, expmonth INT, expyear INT, billzip INT);





