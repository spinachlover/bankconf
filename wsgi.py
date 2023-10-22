#!/usr/bin/env python3

from flask import Flask, request, redirect, render_template, send_file, url_for, make_response
import pandas as pd
import io
import zipfile
import bank_conf as BC
from flask_login import UserMixin, LoginManager, login_required, login_user, logout_user, current_user
# from flask_sqlalchemy import SQLAlchemy
import sqlite3
import secrets
import gunicorn


bankconf = Flask(__name__)
bankconf.secret_key = secrets.token_hex(16)
login_manager = LoginManager()
login_manager.init_app(bankconf)


class User(UserMixin):
    def __init__(self, id: str, password: str):
        self.id = id
        self.password = password

    def get_id(self):
        return self.id

    @staticmethod
    def get(user_id):
        conn = sqlite3.connect('auth.db')
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS users (id TEXT, passwd TEXT)')
        cursor.execute('SELECT id, passwd FROM users WHERE id=?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row is None:
            return None
        return User(row[0], row[1])


@login_manager.user_loader
def load_user(user_id):
    user = User.get(user_id)
    if not user:
        return None
    return user


@bankconf.route('/bankconf/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form['username'].lower().replace(' ', '')
        password = request.form['password']
        user = User.get(user_id)
        if user and user.password == password:
            login_user(user)
            response = make_response(url_for('index'), 302)
            return response
        else:
            response = make_response('Incorrect username or password', 400)
            return response
    return render_template('login.html')


# use the before_request decorator to check if the user is authenticated
# @bankconf.before_request
def before_request():
    if not current_user.is_authenticated and request.endpoint != 'login':  # type:ignore
        return redirect(url_for('login'))


@bankconf.route('/bankconf/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@bankconf.route("/bankconf")
# @login_required
def index():
    return render_template("index.html")


@bankconf.route('/bankconf/download')
def download():
    path = 'template.xlsx'
    return send_file(path, as_attachment=True)


@bankconf.route("/bankconf/process", methods=["POST"])
def process():
    file = request.files["file"]
    company = request.form['company']
    firm = request.form['firm']
    manager = {
        'name': request.form['manager'],
        'email': request.form['email'],
        'tel': request.form['tel']
        }
    dateRange = (request.form['dateStart'], request.form['dateEnd'])
    if not file:
        return redirect("/bankconf")
    if not allowed_file(file.filename):
        return redirect("/bankconf")
    args = (company, manager, dateRange, firm)
    try:
        output = zip_bytes(dict(data_process(file, args)))
        return send_file(
            output,
            download_name="processed_data.zip",
            as_attachment=True,
            # mimetype="application/vnd.ms-excel"
        )
    except Exception as e:
        raise e
        return redirect("/bankconf")


def allowed_file(filename):
    ALLOWED_EXTENSIONS = ['xlsx', 'xls']
    extension = filename.rsplit('.', 1)[1]
    return '.' in filename and extension in ALLOWED_EXTENSIONS


def data_process(file, args):
    df = pd.read_excel(file)
    # find the first blank row
    for i, row in df.iterrows():
        if row.isna().all():
            break
    # slice the dataframe to remove the rows after the first blank row
    df = df.iloc[:i]  # type:ignore
    contexts = BC.const_context(df)
    for context in contexts:
        context.manager = args[1]
        context.dateRange = args[2]
        context.company = args[0]
        context.firm = args[3]
        context.address = '上海市XX区XXXX路XXXX号XX层'
        buffer = io.BytesIO()
        template1 = 'bank_temp.docx'
        template2 = 'bank_temp2.docx'
        template = template1 if context.format == 1 else template2
        filename, tpl = BC.fill_template(vars(context), template)
        tpl.save(buffer)
        buffer.seek(0)
        yield filename, buffer


def zip_bytes(files):
    # Create a byte stream
    bio = io.BytesIO()
    # Create the zip archive
    with zipfile.ZipFile(bio, 'w') as archive:
        for filename, file in files.items():
            archive.writestr(filename, file.getvalue())
    # Return the content of the archive as bytes
    bio.seek(0)
    return bio


if __name__ == "__main__":
    bankconf.run(debug=True, host="0.0.0.0", port=5000)
