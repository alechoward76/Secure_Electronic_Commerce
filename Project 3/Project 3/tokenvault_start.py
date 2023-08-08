# Author: JT Hamrick
# Edits: Codi West
# Token Vault website

import tornado.ioloop
import tornado.web
from tornado.options import define, options
import tornado.template
import MySQLdb
import os
import binascii
import json
import urllib
# From bson import json_util
from random import randint
from Crypto.Cipher import AES
from tornado import httpclient, gen


# Define values for mysql connection
define("port", default=9137, help="run on the given port", type=int)
define("mysql_host", default="127.0.0.1", help="database host")
define("mysql_port", default=3306, help="database port", type=int)
define("mysql_database", default="group8", help="database name")
define("mysql_user", default="group8", help="database user")
define("mysql_password", default="yUIAYjfdQlgoMf2eb5gsqY745ZFKpZZE", help="database password")


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", HomeHandler),
            (r"/genkey", GenerateKeyHandler),
            (r"/issuetoken", IssueTokenHandler),
            (r"/getpan", GetPanHandler)
        ]

        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=False,
            debug=True,
            cookie_secret="hpKckU+P>zqZkzpLbmWE9kLFMfcAvCYLBf6sTsKw6EMg8Kmwtu"
        )
        super(Application, self).__init__(handlers, **settings)
        # Have one global connection to the store DB across all handlers
        self.db = MySQLdb.connect(host=options.mysql_host,
                                    port=options.mysql_port,
                                    db=options.mysql_database,
                                    user=options.mysql_user,
                                    passwd=options.mysql_password)


class BaseHandler(tornado.web.RequestHandler):
    @property
    def db(self):
        return self.application.db


class HomeHandler(BaseHandler):
    ''' Test if tokenvault is running '''
    def get(self):
        self.write("The tokenvault is running")


class GenerateKeyHandler(BaseHandler):
    ''' Generate the key for encrypting sensitive data - only run once '''
    def get(self):
        ekey = os.urandom(32)
        # write the key in hexadecimal format to file
        with open('tv.aes.key', 'w') as keyf:
            keyf.write(ekey.hex())

        self.write({'info': 'key created'})
        self.finish()


class IssueTokenHandler(BaseHandler):
    ''' Take in PAN, send out token of PAN'''
    def get(self):
        self.write("incorrect request type")
        
    def post(self):
        # Need to get PAN, expdate, billzip, billname
        pan = self.get_argument("pan")
        exp_month = self.get_argument("exp_month")
        exp_year = self.get_argument("exp_year")
        billzip = self.get_argument("billzip")
        billname = self.get_argument("billname")

        # Check that all args recieved
        if len(self.request.arguments) != 5:
            # Reset status to bad request
            self.set_status(400)
            return
        
        # Generate a random token
        token = os.urandom(16).hex()

        # Store CC info and token in DB
        ekey = read_aes_key()
        paniv = os.urandom(16)
        enc = AES.new(ekey, AES.MODE_CFB, paniv)
        panc = enc.encrypt(pan)

        # Store CC info/token in database
        sql = f"INSERT INTO panmap(tpan, paniv, panc, expdate, billzip, billname) VALUES (%s, %s, %s, %s, %s, %s)"
        values = (token, paniv, panc, f"{exp_month}-{exp_year}", billzip, billname)
        c = self.db.cursor()
        c.execute(sql, values)
        self.application.db.commit()

        self.write({'status':'success', 'token' : token})
        self.finish()

def read_aes_key():
    with open('tv.aes.key', 'r') as keyf:
        ekey_hex = keyf.read()
        # Convert hex string to bytes
        ekey = bytes.fromhex(ekey_hex)
    return ekey

#Create a new class for GetPanHandler
class GetPanHandler(BaseHandler):
    def get(self):
        self.write("incorrect request type")
    
    @gen.coroutine
    def post(self):
        exp_month = self.get_argument("tpan")
        
       #get pan from database using token
      #  c = self.db.cursor()
       # sql = "SELECT PAN FROM yourtable WHERE token = %s"
       # token = self.get_argument("tpan")
        #c.execute(sql, (token,))

       # result = c.fetchone()
        
        #if result:
            
            #pan = result[0]
      #  else:
          #  pan = None

        #if pan is none, write error
       # if pan is None:
          #  self.write({'status':'error'})
           # self.finish()
          #  return
        

        #if success, write success, etc.
        self.write({'status':'success'})
        self.finish()


        #self.write({'status': 'success'})

        #self.finish()



def main():
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    print(f"Tokenvault started on port: {options.port}")
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
