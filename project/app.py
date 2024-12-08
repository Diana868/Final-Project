import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for, abort, jsonify
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta
from collections import defaultdict

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=5)

db = SQL("sqlite:///orderlyfinance.db")

def table_users():
    db.execute("""CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    hash TEXT NOT NULL);""")
table_users()

def table_income():
    db.execute("""CREATE TABLE IF NOT EXISTS incomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    type_income TEXT,
    income INTEGER,
    month INTEGER,
    FOREIGN KEY(user_id) REFERENCES users(id));""")
table_income()

def table_expenses():
    db.execute("""CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    type_expenses TEXT,
    expenses INTEGER,
    month INTEGER,
    FOREIGN KEY(user_id) REFERENCES users(id));""")
table_expenses()

def table_year():
    db.execute("""CREATE TABLE IF NOT EXISTS year (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    year INTEGER,
    month INTEGER,
    t_income INTEGER,
    t_expenses INTEGER,
    balance INTEGER,
    FOREIGN KEY(user_id) REFERENCES users(id));""")
table_year()

def insert_summary(user_id, total_income_value, total_expenses_value, current_year, current_month):

    balance = total_income_value - total_expenses_value
    check_m = db.execute("SELECT month FROM year WHERE user_id = ? AND year = ? AND month = ?", user_id, current_year, current_month)
    if not check_m:
        try:
            db.execute("INSERT INTO year (user_id, year, month, t_income, t_expenses, balance) VALUES (?, ?, ?, ?, ?, ?)",
                        user_id, current_year, current_month, total_income_value, total_expenses_value, balance)
        except Exception as e:
            flash("Sorry we had an error processing your request, try again please")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    # Register user
    if request.method == "POST" and request.form.get("submitted"):
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username or not password or not confirmation:
            flash("Input cannot be blank")
            return render_template("register.html")

        if password != confirmation:
            flash("Passwords do not match")
            return render_template("register.html")

        finalpassword = generate_password_hash(password, method='scrypt', salt_length=16)
        rows = db.execute("SELECT * FROM users WHERE username = ?", username)
        if len(rows) > 0:
            flash("Username already exists")
            return render_template("register.html")
        else:
            try:
                db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, finalpassword)
            except Exception as e:
                flash("An error occurred: ")
                return render_template("register.html")

        return redirect("/")

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST" and request.form.get("submitted"):
        username = request.form.get("username")
        password = request.form.get("password")
        user = db.execute("SELECT * FROM users WHERE username = ?", username)
        if not username or not password:
            flash("There must be an input")
            return render_template("login.html")
        if not user:
            flash("Username doesn't exist")
            return render_template("login.html")
        if check_password_hash(user[0]['hash'], password):
            session.permanent = True
            session["user_id"] = user[0]["id"]
            session["username"] = user[0]["username"]
            session["hash"] = user[0]["hash"]

            return redirect("/homepage")

    if request.method == "GET":
        return render_template("login.html")

    return render_template("login.html")

@app.route("/income", methods=["GET", "POST"])
def income():
    user_id = session.get("user_id")
    now = datetime.now()
    month = now.month
    year = now.year
    if request.method == "POST":
        if "delete_income" in request.form:
            income_id = request.form.get("income_id")
            db.execute("DELETE FROM incomes WHERE id = ? AND user_id = ?", income_id, user_id)
        else:
            income = request.form.get("income")
            type_income = request.form.get("type_income")
            db.execute("INSERT INTO incomes (user_id, type_income, income, month, year) VALUES (?, ?, ?, ?, ?)",
                       user_id, type_income, income, month, year)
        return redirect("/income")

    incomes = db.execute("SELECT id, type_income, income FROM incomes WHERE user_id = ? AND month = ? AND year = ?",
                         user_id, month, year)
    total_income = db.execute("SELECT SUM(income) AS total FROM incomes WHERE user_id = ? AND month = ? AND year = ?",
                              user_id, month, year)
    total_income_value = total_income[0]['total'] if total_income[0]['total'] is not None else 0
    return render_template("income.html", incomes=incomes, total_income=total_income_value)

@app.route("/expenses", methods=["GET", "POST"])
def expenses():
    user_id = session.get("user_id")
    now = datetime.now()
    month = now.month
    year = now.year
    if request.method == "POST":
        if "delete_income" in request.form:
            expenses_id = request.form.get("expenses_id")
            db.execute("DELETE FROM expenses WHERE id = ? AND user_id = ?", expenses_id, user_id)
        else:
            expenses = request.form.get("expenses")
            type_expenses = request.form.get("type_expenses")
            db.execute("INSERT INTO expenses (user_id, type_expenses, expenses, month, year) VALUES (?, ?, ?, ?, ?)",
                       user_id, type_expenses, expenses, month, year)
        return redirect("/expenses")

    expenses = db.execute("SELECT id, type_expenses, expenses FROM expenses WHERE user_id = ? AND month = ? AND year = ?",
                          user_id, month, year)
    total_expenses = db.execute("SELECT SUM(expenses) AS total FROM expenses WHERE user_id = ? AND month = ? AND year = ?",
                                user_id, month, year)
    total_expenses_value = total_expenses[0]['total'] if total_expenses[0]['total'] is not None else 0
    return render_template("expenses.html", expenses=expenses, total_expenses=total_expenses_value)

@app.route("/year", methods=["GET", "POST"])
def year():
    now = datetime.now()
    current_year = now.year
    current_month = now.month
    user_id = session.get("user_id")
    if user_id is None:
        return redirect("/login")

    total_income = db.execute("SELECT SUM(income) AS total FROM incomes WHERE user_id = ? AND month = ? AND year = ?",
                                                         user_id, current_month, current_year)
    total_income_value = total_income[0]['total'] if total_income[0]['total'] else 0
    total_expenses = db.execute("SELECT SUM(expenses) AS total FROM expenses WHERE user_id = ? AND month = ? AND year = ?",
                                                            user_id, current_month, current_year)
    total_expenses_value = total_expenses[0]['total'] if total_expenses[0]['total'] else 0

    insert_summary(user_id, total_income_value, total_expenses_value, current_year, current_month)

    last_entry = db.execute("SELECT month, year FROM year WHERE user_id = ? ORDER BY year DESC, month DESC LIMIT 1", (user_id))
    if last_entry and (last_entry[0]['month'] != current_month or last_entry[0]['year'] != current_year):
        db.execute("UPDATE incomes SET income = 0 WHERE user_id = ? AND month = ? AND year = ?", user_id, current_month, current_year)
        db.execute("UPDATE expenses SET expenses = 0 WHERE user_id = ? AND month = ? AND year = ?", user_id, current_month, current_year)

    summary = db.execute("SELECT * FROM year WHERE user_id = ?", (user_id))
    grouped_summary = defaultdict(list)
    for row in summary:
        grouped_summary[row["year"]].append(row)
    return render_template("year.html", grouped_summary=grouped_summary)


@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    return redirect("/")

@app.route("/homepage", methods=["GET", "POST"])
def homepage():
    now = datetime.now()
    month = now.month
    year = now.year
    user_id = session.get("user_id")
    total_income = db.execute("SELECT SUM(income) AS total FROM incomes WHERE user_id = ? AND month = ? AND year = ?",
                              user_id, month, year)
    total_expenses = db.execute("SELECT SUM(expenses) AS total FROM expenses WHERE user_id = ? AND month = ? AND year = ?",
                                user_id, month, year)
    show_message = False

    if total_income[0]['total'] is None and total_expenses[0]['total'] is None:
        flash("Welcome to Orderly Finances. Start your journey by registering some incomes and expenses!")
        balance = 0
        show_message = True
    else:
        income_value = total_income[0]['total'] if total_income[0]['total'] is not None else 0
        expense_value = total_expenses[0]['total'] if total_expenses[0]['total'] is not None else 0
        balance = income_value - expense_value
        db.execute("UPDATE year SET t_income = ?, t_expenses = ?, balance = ? WHERE user_id = ? AND year = ? AND month = ?",
                   income_value, expense_value, balance, user_id, year, month)
    return render_template("homepage.html", total_income=total_income[0]['total'], total_expenses=total_expenses[0]['total'],
                           balance=balance, show_message=show_message)

@app.route("/delete_account", methods=["GET", "POST"])
def delete_account():
    if request.method == 'POST':
        user_id = session.get("user_id")
        print(user_id)
        db.execute("DELETE FROM users WHERE id = ?", user_id)
        db.execute("DELETE FROM incomes WHERE user_id = ?", user_id)
        db.execute("DELETE FROM expenses WHERE user_id = ?", user_id)
        db.execute("DELETE FROM year WHERE user_id = ?", user_id)
        session.clear()
    return redirect("/")
