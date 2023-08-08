# Author: JT Hamrick
# design based off of http://chrisdianamedia.com/simplestore/

import json
import os.path
import tornado.ioloop
import tornado.web
from tornado.options import define, options
import tornado.template
import MySQLdb
import uuid
import urllib
import re
import magic

#Testing

#New Imports
import bcrypt

#Project 3
from tornado import httpclient, gen
import json

#salt = bcrypt.gensalt()

# More permanent salt
salt = b'$2b$12$He5y5jJ62fMbXAQemJdDJe'

# define values for mysql connection
define("port", default=8895, help="run on the given port", type=int)
define("mysql_host", default="127.0.0.1", help="database host")
define("mysql_port", default=3306, help="database port", type=int)
define("mysql_database", default="group8", help="database name")
define("mysql_user", default="group8", help="database user")
define("mysql_password", default="yUIAYjfdQlgoMf2eb5gsqY745ZFKpZZE", help="database password")


__UPLOADS__ = "static/uploads/"


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", HomeHandler),
            (r"/details/([^/]+)", DetailsHandler),
            (r"/cart", CartHandler),
            (r"/product/add", AddToCartHandler),
            (r"/product/remove/([^/]+)", RemoveFromCartHandler),
            (r"/cart/empty", EmptyCartHandler),
            (r"/upload", UploadHandler),
            (r"/userform", UserformHandler),
            (r"/welcome/([^/]+)", WelcomeHandler),
            (r"/directory/([^/]+)", DirectoryTraversalHandler),

            #New Handlers
            (r"/login", LoginHandler),
            (r"/logout", LogoutHandler),
            (r"/signup", SignupHandler),
            (r"/account", AccountHandler),

            #New Handlers p3
            (r"/confirm", ConfirmHandler)
            #(r"/thanks", ThanksHandler)
            #(r"/storetoken", StoreTokenHandler)    # Not sure if this is needed yet

        ]
        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            ui_modules={"Small": SmallModule},
            xsrf_cookies=False,
            debug=True,
            cookie_secret="2Xs2dc.y2wqZVB,qRrnyoZuWbUTnjRBG4&uxaMYtM&r%KnpL7e",
            login_url="/login"
        )
        super(Application, self).__init__(handlers, **settings)
        # Have one global connection to the store DB across all handlers
        self.myDB = MySQLdb.connect(host=options.mysql_host,
                                    port=options.mysql_port,
                                    db=options.mysql_database,
                                    user=options.mysql_user,
                                    passwd=options.mysql_password)
        ########################################################################
        #Created user table in the database
      #  c = self.myDB.cursor()
      #  c.execute("CREATE TABLE IF NOT EXISTS info_p3 (id INT NOT NULL AUTO_INCREMENT, username VARCHAR(255), phone_num VARCHAR(255), email VARCHAR(255), hashed_password VARCHAR(255), PRIMARY KEY (id))")

        ##########################################################################



class BaseHandler(tornado.web.RequestHandler):
    @property
    def db(self):
        return self.application.myDB

    # if there is no cookie for the current user generate one
    def get_current_user(self):
        return self.get_secure_cookie("username")
        
       # if not self.get_cookie("username"):
       #     self.set_cookie("webstore_cookie", str(uuid.uuid4()))



#########################################################################
#New Shit


           



#Create a new class for the login handler FINISHED
class LoginHandler(BaseHandler):
    def get(self):
        #authorized = self.get_cookie("loggedin")
        self.render("login.html", error=None)

    def post(self):
        username = self.get_argument("username")
        password = self.get_argument("password")
        hashed_passwordb = bcrypt.hashpw(password.encode('utf8'), salt)
        hashed_password = str(hashed_passwordb, 'utf-8')

        c = self.db.cursor()
        c.execute("SELECT * FROM info_p3 WHERE username = %s AND salt_hash_pass = %s", (username, hashed_password))
        user = c.fetchone()
        if user:  
            # Set cookie fields for later authentication
            #self.set_cookie("loggedin", "true")
            self.set_secure_cookie("username", username)
            self.redirect("/account")
        else:
            self.write("something went wrong")
            #self.redirect("/login")

#Create a new class for the logout handler
class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie("loggedin")
        self.clear_cookie("username")
        self.redirect("/")
        return
    




#Create a new class for conformation handler
class ConfirmHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("confirm.html")

    @gen.coroutine
    def post(self):
        
        cvv = self.get_argument('cvv', None)
        issuer_url = "http://10.10.1.13:9138/paytoken"
        tokenvault_url = "http://10.10.1.13:9137/getpan"
        

        
        


        email = self.get_secure_cookie("user_login")
        c = self.db.cursor(MySQLdb.cursors.DictCursor)
        
        query = "SELECT name, token, email, exp_month, exp_year, zip FROM info_p3 WHERE email = %s"
        parameters = (email, )
        c.execute(query, parameters)
        user_info = c.fetchone()
        print(user_info)

        print(user_info)

        #Get Amount
        cookie = self.get_cookie("username")
        # get the current user's cart based on their cookie
        c = self.db.cursor()
        c.execute("SELECT c.item, \
                          p.price, \
                          p.name, \
                          COUNT(*) AS quantity, \
                          SUM(p.price) AS subtotal, \
                          `options`, \
                          GROUP_CONCAT(c.id) AS `id` \
                   FROM cart c \
                   INNER JOIN products p on p.id = c.item \
                   WHERE c.user_cookie = %s \
                   GROUP BY c.item, c.options", (cookie,))
        products = c.fetchall()
        # calculate total and tax values for cart
        subtotal = float(sum([x[4] for x in products]))
        tax = float("{0:.2f}".format(subtotal * 0.08517))
        shipping = 5.27
        total = subtotal + tax + shipping

        #send the info to the issuer and get a response (Alec)
        
        values = {"token": user_info['token'], 
                "exp_month": user_info['exp_month'], 
                "exp_year": user_info['exp_year'], 
                "name": user_info['name'],
                "billing_zip": user_info['zip'], 
                "amount": total,
                "cvv": cvv,
                "token_vault": tokenvault_url},
        print(user_info)
        print(values)
                
        
        body = urllib.parse.urlencode(values)
        response = yield httpclient.AsyncHTTPClient().fetch(issuer_url, method='POST', body=body, headers=None)
        
         #debug
        
        #print(response.body)
        #print(response.code)

        data = json.loads(response.body)
        #if the response is good
        if data['status'] == 'success':
            self.redirect("/thanks")
        #else
        else:
            self.redirect("/confirm")
        
# Create a new class for the thanks handler
class ThanksHandler(BaseHandler):
    pass

# Create a new class for storetoken handler (if needed)
# class StoreTokenHandler(BaseHandler):
#   pass

#Create a new class for the signup handler FINISHED
class SignupHandler(BaseHandler):
    def get(self):
        #authorized = self.get_cookie("loggedin")
        self.render("signup.html", alert=None)

    @gen.coroutine
    def post(self):
        username = self.get_argument("username")
        phone_num = self.get_argument("phone_num")
        email = self.get_argument("email")
        password = self.get_argument("password")
        confirm = self.get_argument("confirm")
        #Credit Card info
        name = self.get_argument("name")
        address1 = self.get_argument('address1')
        address2 = self.get_argument('address2')
        city = self.get_argument('city')
        state = self.get_argument('state')
        zip_code = self.get_argument('zip_code')
        card_number = self.get_argument('card_number')
        exp_month = self.get_argument('exp_month')
        exp_year = self.get_argument('exp_year')


        #Confirm that the password and confirm password fields match
        if password != confirm:
            self.redirect("/signup")
            return

        #Intermediary step to salt & hash the password
        hashed_passwordb = bcrypt.hashpw(password.encode('utf8'), salt)
        hashed_password = str(hashed_passwordb, 'utf-8')

        # Getting token
        tokenvault_url = "http://10.10.1.13:9137/issuetoken"
        values = {"pan": card_number, "exp_month": exp_month, "exp_year": exp_year, "billzip": zip_code, "billname": name}
        
        body = urllib.parse.urlencode(values)
        response = yield httpclient.AsyncHTTPClient().fetch(tokenvault_url, method='POST', body=body, headers=None)

        #debug
        print(response.body)
        print(response.code)

        data = json.loads(response.body)
        

        #If match, insert into database
        if data['status'] == 'success':
            token = data['token']
            

            #
            query = "INSERT INTO user_info (name, phone_number, email, salt_hash_pass, address1, address2, city, state, zip, exp_month, exp_year, username, token) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            parameters = (name, phone_num, email, hashed_password, address1, address2, city, state, zip_code, exp_month, exp_year, username, token)
            self.db.commit()
            c = self.db.cursor()
            c.execute(query, parameters)
            self.db.commit()

            self.write(f'You have created an account. Log in <a href="/login" class="close">login</a>')
            #self.redirect("/login")
        #return
        else:
            self.write(f'Something went wrong')



#Create a new class for the account handler
class AccountHandler(BaseHandler):
    def get(self):
        authorized = self.get_secure_cookie("username")
        #Return the user to the login page if they are not logged in
        if not authorized:
            self.redirect("/login")
            return
        #If logged in, render the account page
        else:
            # Grab username from cookie
            username = self.get_secure_cookie("username")

            # Get the user's username, phone number, email, and password from the database
            c = self.db.cursor()

            # Grab the username, phone number, email, and password using parameterized query
            c.execute("SELECT * FROM info_p3 WHERE username = %s", (username,))
            user = c.fetchone()

            # Render the user's data on the page
            self.render("account.html", user=user)
        

    
   #WIP v
   
    #Select the user's information from the database
    




#########################################################################


class HomeHandler(BaseHandler):
    def get(self):
        # get all products in the database for the store's main page
        temp = []
        c = self.db.cursor()
        c.execute("SELECT * FROM products")
        products = c.fetchall()
        # add urlencoded string to tuple for product image link
        for k, v in enumerate(products):
            temp.append(products[k] + (urllib.parse.quote_plus(products[k][2]),))

        authorized = self.get_secure_cookie("username")
        self.render("home.html", products=tuple(temp), auth=authorized)


class DetailsHandler(BaseHandler):
    def get(self, slug):
        # get the selected product from the database
        temp = []
        # remove non numerical characters from slug
        item_number = re.findall(r'\d+', slug)
        c = self.db.cursor()
        c.execute("SELECT * \
                   FROM products p \
                   LEFT JOIN (SELECT `option`, \
                                     GROUP_CONCAT(`value`) AS `value`, \
                                     product_id \
                         FROM `product_options` \
                         WHERE `product_id` = " + item_number[0] + " \
                         GROUP BY `option`) AS o ON o.product_id = p.id \
                   WHERE p.id = " + item_number[0])
        product = c.fetchall()
        # add urlencoded string to tuple for product image link
        quoted_url = urllib.parse.quote_plus(urllib.parse.quote_plus(product[0][2]))
        temp.append(product[0] + (quoted_url,))

        authorized = self.get_cookie("username")
        self.render("details.html",
                    product=tuple(temp),
                    sku=item_number[0],
                    auth=authorized)


class CartHandler(BaseHandler):
    def get(self):
        # get the current user's cookie
        #cookie = self.get_cookie("loggedin")
        cookie = self.get_secure_cookie("username")
        
        # get all products in the user's cart
        c = self.db.cursor()
        c = self.db.cursor()
        c.execute("SELECT c.item, \
                                p.price, \
                                p.name, \
                                COUNT(*) AS quantity, \
                                SUM(p.price) AS subtotal, \
                                `options`, \
                                GROUP_CONCAT(c.id) AS `id` \
                        FROM cart c \
                        INNER JOIN products p on p.id = c.item \
                        WHERE c.user_cookie = %s \
                        GROUP BY c.item, c.options", (cookie,))        
        products = c.fetchall()
        # calculate total and tax values for cart
        total = float(sum([x[4] for x in products]))
        count = sum([x[3] for x in products])
        tax = float("{0:.2f}".format(total * 0.08517))
        shipping = 5.27

        if not total:
            shipping = 0.00

        authorized = self.get_cookie("loggedin")
        self.render("cart.html",
                    products=products,
                    total=total,
                    count=count,
                    shipping=shipping,
                    tax=tax,
                    auth=authorized)


class AddToCartHandler(BaseHandler):
    def post(self):
       # get the product information from the details page
        id = self.get_argument("product", None)
        #cookie = self.get_cookie("loggedin")
        cookie = self.get_secure_cookie("username")
        product_options = ",".join(self.get_arguments("option"))
        # add the product to the user's cart
        c = self.db.cursor()
        #insert the id, user cookie, item, and options into the cart table
        c.execute("INSERT INTO cart (id, user_cookie, item, options) \
                   VALUES (%s, %s, %s, %s)", (0, cookie, id, product_options))

        self.application.myDB.commit()
        self.redirect("/cart")

        

class RemoveFromCartHandler(BaseHandler):
    def get(self, slug):
        # get the current user's cookie
        #cookie = self.get_cookie("loggedin")
        cookie = self.get_secure_cookie("username")
        # use that cookie to remove selected item from the user's cart
        c = self.db.cursor()
        c.execute("DELETE FROM cart \
                   WHERE user_cookie = %s \
                       AND id IN (%s)", (cookie, slug))

        self.application.myDB.commit()
        self.redirect("/cart")


class EmptyCartHandler(BaseHandler):
    def get(self):
        # get the current user's cookie
        #cookie = self.get_cookie("loggedin")
        cookie = self.get_secure_cookie("username")
        # use that cookie to remove all items from user's cart
        c = self.db.cursor()
        c.execute("DELETE FROM cart WHERE user_cookie = {0}".format(cookie))
        self.application.myDB.commit()
        self.redirect("/cart")


class WelcomeHandler(BaseHandler):
    def get(self, name):
        TEMPLATE = open("templates/welcome.html").read()
       	#template_data = TEMPLATE.replace("FOO" , name)
        t = tornado.template.Template(TEMPLATE)
        self.write(t.generate(name=name))

class UserformHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("fileuploadform.html")


class UploadHandler(tornado.web.RequestHandler):
    def post(self):
        fileinfo = self.request.files['filearg'][0]
        fname = fileinfo['filename']
        # extn = os.path.splitext(fname)[1]
        # cname = str(uuid.uuid4()) + extn
        fh = open(__UPLOADS__ + fname, 'w')
        fh.write(fileinfo['body'])
        self.finish(fname + " is uploaded!! Check %s folder" % __UPLOADS__)
        # self.write(fileinfo)


class DirectoryTraversalHandler(BaseHandler):
    def get(self, slug):
        mime = magic.Magic(mime=True)
        filename = urllib.parse.unquote(urllib.parse.unquote(slug))
       #################################################
        expDir = '/directory/'
        path = os.path.abspath(os.path.join(expDir, filename))
        if  path.startswith(expDir):
              raise tornado.web.HTTPError(400)
       #################################################
        mime_type = mime.from_file(filename)
        self.set_header('Content-Type', mime_type)
        with open(filename, 'rb') as f:
            self.write(f.read())


class SmallModule(tornado.web.UIModule):
    def render(self, item):
        return self.render_string("modules/small.html", item=item)

#Class 

def main():
    http_server = tornado.httpserver.HTTPServer(Application(), ssl_options={"certfile": os.path.join("certs/host.cert"), "keyfile":os.path.join("certs/host.key"), })
    http_server.listen(options.port)
    print(f"Web server started. In your browser, go to 10.10.0.13:{options.port}")
    tornado.ioloop.IOLoop.current().start()
    
    

if __name__ == "__main__":
    main()
