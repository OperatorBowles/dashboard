import sqlite3
from datetime import datetime
from sqlite3 import Error
from flask import Flask, redirect, request, render_template, session
from flask_session import Session

app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

DATABASE = r'health.db'
ACTIVITY = ["Sedentary", 
            "Lightly Active", 
            "Moderately Active", 
            "Very Active", 
            "Extremely Active"]
GOALS = ["Weight Loss", 
        "Maintenance", 
        "Bulking"]

# Setting up the program with admin functions

def create_connection(db_file):
    # Create a database connection to a SQLite database
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(e)

    return conn

def create_table(conn, create_table_sql):
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except Error as e:
        print(e)

def get_user(email):
    conn = create_connection(DATABASE)
    cur = conn.cursor()
    try:
        if cur.execute("SELECT EXISTS(SELECT first_name FROM users WHERE email=?)", (email,)).fetchone() == (1,):
            r = cur.execute("SELECT first_name FROM users WHERE email=?", (email,)).fetchone()
            return r[0]
    except:
        print("User does not exist. Please register first.")

def register_user(conn, user):
    sql = ''' INSERT INTO users(email, first_name, last_name, password, age, sex, height, weight, goal, activity) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) '''
    cur = conn.cursor()
    cur.execute(sql, user)

    # Update tracking table with first instance
    cur.execute("INSERT INTO tracking(email, entry_date, weight, goal, activity) VALUES (?, ?, ?, ?, ?)", (user[0], datetime.now(), user[7], user[8], user[9]))
    
    # Update current_goals table with Carb, Protein, and Fat (g) goals
    metrics = (user[6], user[7], user[4], user[5], user[8], user[9])
    user_metrics = get_macros(metrics)
    cur.execute("INSERT INTO current_goals(email, goal, activity, calories, carbs, protein, fats) VALUES (?,?,?,?,?,?,?)", (user[0], user[8], user[9], user_metrics[0], user_metrics[1], user_metrics[2], user_metrics[3]))
    
    conn.commit()

def check_user(conn, user):
    cur = conn.cursor()
    if cur.execute("SELECT EXISTS(SELECT 1 FROM users WHERE name=?)", (user,)).fetchone() == (1,):
        return 1

# Below code is for the program menu

def add_macros(conn, entry):
    sql = ''' INSERT INTO tracking(name, entry_date, carbs, protein, fats, goal, activity) VALUES (?, ?, ?, ?, ?, ?, ?) '''
    cur = conn.cursor()
    cur.execute(sql, entry)
    conn.commit()
    print("Added new entry for macros")

def update_weight(conn, user, weight):
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Grab the old weight and then update the Users table with the new weight
    old_weight = cur.execute("SELECT weight FROM users WHERE name=?", (user,)).fetchone()
    cur.execute("UPDATE users SET weight=? WHERE name=?", (weight, user,))
    
    # Insert the new weight into the tracking table with current date/time
    sql = '''INSERT INTO tracking(name, entry_date, weight) VALUES (?,?,?)'''
    cur.execute(sql, (user, datetime.now(), weight))

    # Tell user old weight changed to new weight
    print(f'''Weight successfully updated from {int(old_weight["Weight"])} to {weight}.''')

@app.route("/goals", methods=["GET", "POST"])
def update_goal():
    if request.method == "POST":
        conn = create_connection(DATABASE)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Grab the old weight and then update the Users table with the new weight
        old_goal = cur.execute("SELECT goal FROM users WHERE name=?", (user,)).fetchone()
        cur.execute("UPDATE users SET goal=? WHERE name=?", (goal, user,))

        # Insert the new weight into the tracking table with current date/time
        sql = '''INSERT INTO tracking(name, entry_date, goal) VALUES (?,?,?)'''
        cur.execute(sql, (user, datetime.now(), goal))
        
        print(f'''Goal successfully updated from {old_goal["Goal"]} to {goal}.''')
    else:
        return render_template("goals.html")

def update_activity(conn, user, activity):
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Grab the old activity level and then update the Users table with the new activity level
    old_activity = cur.execute("SELECT activity FROM users WHERE name=?", (user,)).fetchone()
    cur.execute("UPDATE users SET activity=? WHERE name=?", (activity, user,))

    # Insert the new weight into the tracking table with current date/time
    sql = '''INSERT INTO tracking(name, entry_date, activity) VALUES (?,?,?)'''
    cur.execute(sql, (user, datetime.now(), activity))
    
    print(f'''Activity level successfully updated from {old_activity["Activity"]} to {activity}.''')

def get_macros(metrics):
    
    height=int(metrics[0])
    weight=int(metrics[1])
    age=int(metrics[2])

    if metrics[3] == "M":
        bmr = 66 + (6.23*weight) + (12.7*height) - (6.8*age)
    else:
        bmr = 655 + (4.35*weight) + (4.7*height) - (4.7*age)

    # Multiply BMR by TDEE
    if metrics[4] == "sedentary":
        bmr = bmr*1.2
    elif metrics[4] == "lightly_active":
        bmr = bmr*1.375
    elif metrics[4] == "moderately_active":
        bmr = bmr*1.55
    elif metrics[4] == "very_active":
        bmr = bmr*1.725
    else:
        bmr = bmr*1.9

    # Get macros based on new BMR
    if metrics[5] == "weight_loss":
        carbs = bmr*.35
        protein = bmr*.45
        fats = bmr*.2
    elif metrics[5] == "maintenance":
        carbs = bmr*.45
        protein = bmr*.3
        fats = bmr*.25
    else:
        carbs = bmr*.45
        protein = bmr*.35
        fats = bmr*.2

    user_metrics = (int(bmr), int(carbs/4), int(protein/4), int(fats/4))
    return(user_metrics)
    
def pull_results(conn, user):
    cur = conn.cursor()
    # Check if the user exists in the Tracking table
    if cur.execute("SELECT EXISTS(SELECT * FROM tracking WHERE name=?)", (user,)).fetchone() == (1,):
        r = cur.execute("SELECT * FROM tracking WHERE name=? ORDER BY entry_date ASC LIMIT 10", (user,)).fetchall() # Limit results to last 10
        # Print each row
        for row in r:
            print(row)
    else:
        print("No data currently exists.")
    
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        session["email"] = request.form.get("email")
        session["name"] = get_user(session["email"])
        return redirect("/")
    return render_template("login.html")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        
        if request.form.get("password") == request.form.get("confirm_password"):
            session["name"] = request.form.get("first_name")
            session["email"] = request.form.get("email")
            
            # Get variables from the form
            email = request.form.get("email")
            first_name = request.form.get("first_name")
            last_name = request.form.get("last_name")
            password = request.form.get("password")
            age = request.form.get("age")
            sex = request.form.get("sex")
            height = request.form.get("height")
            weight = request.form.get("weight")
            goal = request.form.get("goal")
            activity = request.form.get("activity")

            # Register the new user
            user = (email, first_name, last_name, password, age, sex, height, weight, goal, activity)
            conn = create_connection(DATABASE)
            register_user(conn, user)

            return redirect("/")
        else:
            return render_template("register.html")
    
    sql_create_users_table = """ CREATE TABLE IF NOT EXISTS users (
                                    email text PRIMARY KEY,
                                    first_name text NOT NULL,
                                    last_name text NOT NULL,
                                    password text NOT NULL,
                                    age integer NOT NULL,
                                    sex text NOT NULL,
                                    height float NOT NULL,
                                    weight float NOT NULL,
                                    goal text NOT NULL,
                                    activity text NOT NULL
                                );"""

    sql_create_tracking_table = """ CREATE TABLE IF NOT EXISTS tracking (
                                    id integer PRIMARY KEY,
                                    email text NOT NULL,
                                    entry_date text NOT NULL,
                                    weight float,
                                    carbs integer,
                                    protein integer,
                                    fats integer, 
                                    goal text,
                                    activity text
                                );"""

    sql_create_current_goals_table = """ CREATE TABLE IF NOT EXISTS current_goals (
                                        email text PRIMARY KEY,
                                        goal text,
                                        activity text,
                                        calories integer,
                                        carbs integer,
                                        protein integer,
                                        fats integer
                                    );"""

    conn = create_connection(DATABASE)
    if conn is not None:
        # Create tables
        create_table(conn, sql_create_users_table)
        create_table(conn, sql_create_tracking_table)
        create_table(conn, sql_create_current_goals_table)
        conn.commit()
    else:
        print("Error! Cannot create the database connection.")
    
    return render_template("register.html")

@app.route("/logout")
def logout():
    session["email"] = None
    session["name"] = None
    return redirect("/")

@app.route("/settings")
def settings():
    if request.method == "POST":
        print('TODO')
    else:
        return render_template("settings.html")