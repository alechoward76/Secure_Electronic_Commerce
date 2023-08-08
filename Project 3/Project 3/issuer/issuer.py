# Author: JT Hamrick
# Edits: Codi West
# Issuer Website

import os.path
import tornado.ioloop
import tornado.web
from tornado.options import define, options
import tornado.template
from tornado import httpclient, gen
import MySQLdb
import urllib
# import binascii
from Crypto.Cipher import AES
import json
# from bson import json_util
import datetime
from aes_helper import read_aes_key
import logging


# Define values for mysql connection
define("port", default=9138, help="run on the given port", type=int)
define("mysql_host", default="127.0.0.1", help="database host")
define("mysql_port", default=3306, help="database port", type=int)
define("mysql_database", default="ccissuer", help="database name")
define("mysql_user", default="ccissuer", help="database user")
define("mysql_password", default="Xkm5acYX8UFTGbi63CpfI1c7H5ksDsih", help="database password")


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", HomeHandler),
            (r"/paytoken", RetrievePayTokenHandler),
            (r"/paypan", RetrievePayPanHandler),
            (r"/authlocal", AuthLocalHandler)
        ]
        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=False,
            debug=True,
            cookie_secret="Z3woPEfNVQCEs2dUTKqRKjc7Tpk2EtDzzj@LnXmhvAF]chNzoM"
        )
        super(Application, self).__init__(handlers, **settings)
        # Have one global connection to the store DB across all handlers

        self.connect_DB()

    def connect_DB(self):
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
    def get(self):
        self.render("home.html")


class RetrievePayTokenHandler(BaseHandler):
    ''' /paytoken '''
    def get(self):
        self.write("incorrect request type")

    @gen.coroutine
    def post(self):
        tpan = self.get_argument("tpan")
        exp_month = self.get_argument("exp_month")
        exp_year = self.get_argument("exp_year")
        name = self.get_argument("name")
        billing_zip = self.get_argument("billing_zip")
        order_total = self.get_argument("amount")
        cvv = self.get_argument("cvv")
        tv_url = self.get_argument("token_vault", "none")

        # remote_ip = self.remote_ip

        expdate = datetime.datetime(int(exp_year), int(exp_month), 1)
        order_time = datetime.datetime.now()

        try:
            sql = "INSERT INTO auth (tpan, cvv, exp_date, amount, name, billzip, merchant, timestamp, authorization) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
            values = tpan, cvv, expdate, order_total, name, billing_zip, "Classic Store", order_time, "PENDING"
            c = self.db.cursor()
            # c.execute("INSERT INTO auth (tpan, cvv, exp_date, amount, name, billzip, merchant, timestamp, authorization) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", (tpan, cvv, expdate, order_total, name, billing_zip, "Classic Store", order_time, "PENDING"))
            c.execute(sql, values)
            self.db.commit()

            # Only if token vault has been provided
            if (tv_url != "none"):
                # url = 'http://127.0.0.1:8887/getpan'
                # print(tv_url)
                values = {'tpan': tpan}
                body = urllib.parse.urlencode(values)
                logging.warning(values)

                response = yield httpclient.AsyncHTTPClient().fetch(tv_url, method='POST', body=body, headers=None)

                logging.warning(response)

                d = json.loads(response.body)

                if d['status'] == 'success':
                    self.write({'status': 'success'})
                else:
                    self.write({'status': 'error', 'info': d['info']})
                self.finish()
            else:
                self.write(json.dumps({'status': 'missing token_vault parameter'}))
                self.finish()

        except:# Exception as e:
            self.write({'status': 'error', 'info': 'Server encountered an error. Refreshing DB connection. Try again.'})#, 'stack', e})
            self.finish()
            self.application.connect_DB()


class RetrievePayPanHandler(BaseHandler):
    ''' /paypan '''
    def get(self):
        self.write("incorrect request type")

    def post(self):
        # Note: inputs from POST are strings
        inputtoken = self.get_argument("token")
        inputpan = self.get_argument("pan")

        # ekey_hex = "dd25176c94efc38e3407a1947e40247fa62a9fd8a45085701827c4cca6ca5198"
        # ekey = binascii.a2b_hex(ekeyhex)
        # ekey = bytes.fromhex(ekey_hex)
        ekey = read_aes_key()

        # c = self.db.cursor() # Only works with deprecated torndb driver
        c = self.db.cursor(MySQLdb.cursors.DictCursor)
        c.execute("SELECT * FROM ccinfo")
        ccinfo = c.fetchall()

        name = ""
        bzip = ""
        success = False

        # logging.warning(ccinfo)
        logging.warning(type(inputpan))
        logging.warning(inputtoken)

        for key, value in enumerate(ccinfo):
            # Decrypt pan from issuer database
            dec = AES.new(ekey, AES.MODE_CFB, value['ivpan'])
            # Note: this is interpreted in Python 3 as bytes
            # Thus, decode bytes into a string for comparison, otherwise always False
            pan = dec.decrypt(value['pan']).decode('utf-8')

            # Check if pan provided by token_vault matches a legit card in database
            logging.warning(f"Does {pan} match input {inputpan}? {pan == inputpan}")
            if pan == inputpan:
                name = value['customer']
                bzip = value['billzip']
                success = True

                break

        # Update auth record as approved or rejected depending on card legitimacy
        c = self.db.cursor(MySQLdb.cursors.DictCursor)
        c.execute("SELECT name, billzip FROM auth WHERE tpan = %s", (inputtoken,))
        auth = c.fetchone()

        if success and (auth['name'] == name) and (int(bzip) == int(auth['billzip'])):
            sql = "UPDATE `auth` SET `authorization` = 'APPROVED' WHERE `tpan` = %s"
        else:
            sql = "UPDATE `auth` SET `authorization` = 'REJECTED' WHERE `tpan` = %s"
            success = False
        logging.warning(f"{auth['name']} is  {name}?")
        logging.warning(f"{(auth['name'] == name)} and {int(bzip) == int(auth['billzip'])}")

        c = self.db.cursor()
        c.execute(sql, (inputtoken,))
        self.db.commit()

        # Return result
        if success:
            self.write(json.dumps({'status': 'success'}))#, default=json_util.default))
        else:
            self.write(json.dumps({'status': 'error',
                                   'info': 'no matching cc in ccinfo table'}))#, default=json_util.default))
        self.finish()


class AuthLocalHandler(BaseHandler):
    ''' This function is purely for testing that the issuer is working and providing "valid" cards to test with '''
    def get(self):
        # ekeyhex = "dd25176c94efc38e3407a1947e40247fa62a9fd8a45085701827c4cca6ca5198"
        # ekey = bytes.fromhex(ekey_hex)
        ekey = read_aes_key()

        # expmonth  = 4
        # expyear   = 2019
        # billzip   = 75214
        # customer  = "Gerald Turner"
        # pan       = "3456789012345678"
        # cvv       = "668"

        # ccinfo = self.db.query("SELECT * FROM ccinfo")
        c = self.db.cursor(MySQLdb.cursors.DictCursor)
        c.execute("SELECT * FROM ccinfo")
        ccinfo = c.fetchall()

        card_list = []
        for value in ccinfo:
            dec = AES.new(ekey, AES.MODE_CFB, value['ivcvv'])
            ppp = AES.new(ekey, AES.MODE_CFB, value['ivpan'])
            dbcvv = dec.decrypt(value['cvv']).decode('utf-8')
            panvv = ppp.decrypt(value['pan']).decode('utf-8')

            # Create dictionary for individual card and append to dictionary of all card info
            card_list.append({"cvv": dbcvv, "pan": panvv, "expmonth": value['expmonth'], "expyear": value['expyear'], "zip": value['billzip'], "customer": value['customer']})
            # self.write("cvv: " + str(dbcvv) + "\n")
            # self.write("pan: " + str(panvv) + "\n")
            # self.write("expmonth: " + str(value['expmonth']) + "\n")
            # self.write("expyear: " + str(value['expyear']) + "\n")
            # self.write("zip: " + str(value['billzip']) + "\n")
            # self.write("customer: " + str(value['customer']) + "\n\n")

        # print(card_list)

        #self.set_header("Content-Type", "application/json")
        self.write({'status': 'success', 'cards': card_list})
        self.finish()


def main():
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    print(f"Listening on port: {options.port}")
    tornado.ioloop.IOLoop.current().start()

if __name__ == "__main__":
    main()
