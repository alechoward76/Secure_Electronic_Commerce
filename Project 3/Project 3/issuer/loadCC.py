#!/usr/bin/env python

# GRANT ALL PRIVILEGES ON ccissuer.* To 'issuer'@'localhost' IDENTIFIED BY 'HamsterEMV';
# create table ccinfo (ivpan BLOB, pan BLOB, ivcvv BLOB, cvv BLOB, expmonth INT, expyear INT, billzip INT, customer VARCHAR(40),primary key (expmonth,expyear,billzip,customer));

# create database tv;
# use tv;
# GRANT ALL PRIVILEGES ON tv.* To 'tokenv'@'localhost' IDENTIFIED BY 'IndirectionRocks';


import os
# import binascii
from Crypto.Cipher import AES
import MySQLdb
from aes_helper import gen_aes_key, read_aes_key

def connect_db():
    conn = MySQLdb.connect(
        host="127.0.0.1",
        port=3306,
        db='ccissuer',
        user='ccissuer',
        passwd='Xkm5acYX8UFTGbi63CpfI1c7H5ksDsih')
    return conn


def del_ccnums(ekey):
    ''' Delete all Credit Card numbers from database '''
    conn = connect_db()
    c = conn.cursor()

    # sql = "DELETE FROM ccinfo;"
    sql = "TRUNCATE TABLE ccinfo;" # Faster but irrecoverable
    c.execute(sql)

    conn.commit()

    print("Deleted all credit card info from database")


def insert_ccnums(ekey):
    ''' Insert Credit Card numbers to database '''
    conn = connect_db()
    c = conn.cursor()

    for line in open("./ccnums.csv"):
        (pan, cvv, expmonth, expyear, billzip, name) = line.split(',')
        name = name.strip()
        # generate random initialization vector
        paniv = os.urandom(16)
        # Encryption
        enc = AES.new(ekey, AES.MODE_CFB, paniv)
        panc = enc.encrypt(pan)
        # cvv
        cvviv = os.urandom(16)
        cvvenc = AES.new(ekey, AES.MODE_CFB, cvviv)
        cvvc = cvvenc.encrypt(cvv)
        stmt = "INSERT INTO ccinfo values (%s,%s,%s,%s,%s,%s,%s,%s);"
        c.execute(stmt, (paniv, panc, cvviv, cvvc, expmonth, expyear, billzip, name))

    conn.commit()

    print("Inserted credit card info to database")


if __name__ == "__main__":

    # Only create key on first run
    gen_aes_key()

    ekey = read_aes_key()

    del_ccnums(ekey)
    insert_ccnums(ekey)


# Decryption
# ekey = open('./issuer.aes.key').read()
# dec = AES.new(fkey, AES.MODE_CFB, paniv)
# panp = dec.decrypt(panc)
