from flask import Flask, render_template, redirect, request
from flask_mysqldb import MySQL
from functools import wraps

import MySQLdb.cursors
import re
import bcrypt
import logging
import uuid
import time
import threading

app = Flask(__name__, template_folder="pages", static_folder="static", static_url_path="/static")

# DB Connction Details
app.config['MYSQL_HOST'] = '35.245.122.87'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'password'
app.config['MYSQL_DB'] = 'webshell'

# Intialize MySQL
mysql = MySQL(app)

# Registration Code
app.config['REGISTRATION_CODE'] = 'letmein'

# Expiration time, seconds
app.config['SESSION_EXPIRATION'] = 604800


# Decorators 
def require_user(f):
    @wraps(f)
    def authenticate(*args, **kwargs):

        # Retrieve and decode token, else error
        if not ("Session" in request.cookies): return redirect("login")

        # Attempt to retrieve user's pw hash from the db 
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        sql_get_session = ("SELECT * FROM sessions WHERE session_id = %s")
        cursor.execute(sql_get_session, (request.cookies['Session'],))
        attempted_sesssion = cursor.fetchone()
        
        if not attempted_sesssion: return redirect("login")

        # Validate session expiration 
        session_age = int(time.time()) - attempted_sesssion['epoch']
        if session_age > app.config['SESSION_EXPIRATION']: # 1 Week
            return redirect("login")

        #TODO UPDATE EPOCH

        # Retrieve name for session and append
        session_user_id = attempted_sesssion['user_id']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        sql_get_account = ("SELECT * FROM accounts WHERE user_id = %s")
        cursor.execute(sql_get_account, (session_user_id,))
        attempted_account = cursor.fetchone()

        kwargs['human_name'] = attempted_account['human_name']

        # Authentication has passed, return original request
        return f(*args, **kwargs)
    return authenticate


@app.route("/")
def root():
    return redirect("/shell")


@app.route("/about")
def about(): 
    # Retrieve and decode token, else render unauthenticated
    if "Session" in request.cookies:
        # Attempt to retrieve user's pw hash from the db 
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        sql_get_session = ("SELECT * FROM sessions WHERE session_id = %s")
        cursor.execute(sql_get_session, (request.cookies['Session'],))
        attempted_sesssion = cursor.fetchone()
        
        if not attempted_sesssion: return render_template("about.html")

        # Validate session expiration 
        session_age = int(time.time()) - attempted_sesssion['epoch']
        if session_age > app.config['SESSION_EXPIRATION']: # 1 Week
            return render_template("about.html")

        # Retrieve name for session and append
        session_user_id = attempted_sesssion['user_id']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        sql_get_account = ("SELECT * FROM accounts WHERE user_id = %s")
        cursor.execute(sql_get_account, (session_user_id,))
        attempted_account = cursor.fetchone()
        
        return render_template("about.html", user=attempted_account['human_name'])
    
    
    return render_template("about.html")


@app.route("/logout")
@require_user
def logout(*args, **kwargs):
    # Purge the session from the database
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    sql_purge_session = ("DELETE FROM sessions WHERE session_id = %s")
    cursor.execute(sql_purge_session, (request.cookies['Session'],))
    mysql.connection.commit()
    
    return redirect("/login", code=302)


@app.route("/login", methods=['GET', 'POST'])
def login():
    # provide authentication page
    if request.method == 'GET': return render_template("login.html")

    # attempt authentication
    if request.method == 'POST':
        attempted_username = request.form['username']
        attempted_password = request.form['password']

        logging.info(f"Login attempted with {attempted_username}:{attempted_password}")

        # attempt to retrieve user's pw hash from the db 
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        sql_get_pwhash = ("SELECT * FROM accounts WHERE username = %s")
        cursor.execute(sql_get_pwhash, (attempted_username,))
        attempted_user = cursor.fetchone()
        
        # only continue if user exists in db
        if attempted_user:
            actual_password_hashed = attempted_user['password_hash']
            
            # validate password
            if bcrypt.checkpw(attempted_password.encode('ascii'), actual_password_hashed.encode('ascii')):
                # create session
                new_session_id = str(uuid.uuid1())
                sql_query_session = "INSERT INTO `sessions` VALUES (%(session_id)s, %(user_id)s, %(epoch)s);"
                sql_data_session = {
                    'session_id': new_session_id,
                    'user_id': attempted_user['user_id'],
                    'epoch': int(time.time())
                }

                cursor.execute(sql_query_session, sql_data_session)
                mysql.connection.commit()

                logging.info(f"New session, {new_session_id} for user {attempted_user['user_id']}")

                response = redirect("/shell")
                response.set_cookie('Session', new_session_id)
                return response

            else:
                logging.error(f'Invalid password {attempted_password} for user {attempted_username}')
        else:
            logging.error(f'No user {attempted_username}')

        return render_template("login.html", bad_login="credentials")


@app.route("/register", methods=['GET', 'POST'])
def register():
    # provide registration page
    if request.method == 'GET': return render_template("register.html")
    
    # attempt registration
    if request.method == 'POST':
        human_name = request.form['humanname']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        registration_code = request.form['code']

        print(f"name {human_name}\nemail {email}\nusername {username}\npassword {password}\ncode {registration_code}\n")
        
        email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        if not re.fullmatch(email_regex, email):
            return render_template("register.html", bad_registration="email")

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # see if email exists
        sql_get_user = ("SELECT * FROM accounts WHERE email = %s")
        cursor.execute(sql_get_user, (email,))
        retreived_user = cursor.fetchone()
        if retreived_user: return render_template("register.html", bad_registration="email")

        # see if username exists
        sql_get_user = ("SELECT * FROM accounts WHERE username = %s")
        cursor.execute(sql_get_user, (username,))
        retreived_user = cursor.fetchone()
        if retreived_user: return render_template("register.html", bad_registration="username")
        
        # validate registration code
        if registration_code != app.config['REGISTRATION_CODE']: 
            return render_template("register.html", bad_registration="code")

        # everything checks out, lets register the new user
        sql_query_newuser = "INSERT INTO `accounts` VALUES (%(user_id)s, %(human_name)s, %(email)s, %(username)s, %(password_hash)s);"
        sql_data_newuser = {
            'user_id': uuid.uuid1(),
            'human_name': human_name,
            'email': email,
            'username': username,
            'password_hash': bcrypt.hashpw(password.encode('ascii'), bcrypt.gensalt()).decode('ascii')
        }

        cursor.execute(sql_query_newuser, sql_data_newuser)
        mysql.connection.commit()

        logging.info(f"Registered new user, {username}")
        
        return redirect("/login", code=302)


@app.route("/shell")
@require_user
def shell(*args, **kwargs):
    return render_template("shell.html", user=kwargs['human_name'])


def purge_stale_sessions():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    sql_purge_session = ("DELETE FROM sessions WHERE session_id IN ("
                         "SELECT session_id, epoch FROM sessions WHERE (%s - epoch)>%s"
                         ")")
    cursor.execute(sql_purge_session, (int(time.time()), app.config['SESSION_EXPIRATION'],))
    mysql.connection.commit()

    # wait for an hour befores rerunning
    time.sleep(60*60)


def main():
    thread_purge_stale_sessions = threading.Thread(target=purge_stale_sessions)
    thread_purge_stale_sessions.start()

    app.run()

    thread_purge_stale_sessions.join()


if __name__ == "__main__":
    main()