from flask import Flask, render_template, request, redirect, session
import mysql.connector
import os

app = Flask(__name__)
app.secret_key = "nettech_secret_key"

def get_db():
    return mysql.connector.connect(
        host=os.environ.get("MYSQLHOST"),
        port=int(os.environ.get("MYSQLPORT", 3306)),
        user=os.environ.get("MYSQLUSER"),
        password=os.environ.get("MYSQLPASSWORD"),
        database=os.environ.get("MYSQLDATABASE")
    )

def get_user():

    if "user_id" not in session:
        return None

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""SELECT * FROM users WHERE id = %s""", (session["user_id"],))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

def init_db():

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS users ( id INT AUTO_INCREMENT PRIMARY KEY, username VARCHAR(100) UNIQUE NOT NULL,email VARCHAR(150) UNIQUE NOT NULL,password VARCHAR(255) NOT NULL)""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS tickets (id INT AUTO_INCREMENT PRIMARY KEY, username VARCHAR(100) NOT NULL, subject VARCHAR(255) NOT NULL, description TEXT NOT NULL, priority VARCHAR(50) NOT NULL DEFAULT 'Medium', status VARCHAR(50) DEFAULT 'Pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    cursor.execute( """SELECT id FROM users WHERE username = %s """, ("user",))
    existing_user = cursor.fetchone()

    if existing_user is None:
        cursor.execute(""" INSERT INTO users (username, email, password) VALUES (%s, %s, %s) """,("user","user@example.com","12345"))
        print("Default user created.")

    else:
        print("Default user already exists.")

    conn.commit()
    cursor.close()
    conn.close()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/userLogin", methods=["GET", "POST"])
def userLogin():

    if request.method == "POST":

        username = request.form.get("username","").strip()
        password = request.form.get("password","")

        if not username or not password:

            return render_template("userLogin.html",error="Username and password are required.")
        
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(""" SELECT * FROM users WHERE username = %s """, (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and user["password"] == password:

            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect("/userDashboard")

        return render_template("userLogin.html",error="Invalid username or password.")
    return render_template("userLogin.html")

@app.route("/userRegistration", methods=["GET", "POST"])
def userRegistration():

    if request.method == "POST":

        username = request.form.get("username","").strip()
        email = request.form.get("email","").strip()
        password = request.form.get("password","")
        confirm_password = request.form.get("confirm_password","")

        if (
            not username
            or not email
            or not password
            or not confirm_password
        ):
            return render_template("userRegistration.html",error="All fields are required.")

        if password != confirm_password:

            return render_template("userRegistration.html", error="Passwords do not match.")

        if len(password) < 5:

            return render_template("userRegistration.html",error="Password must be at least 5 characters.")

        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(""" SELECT id FROM users WHERE username = %s""",(username,))
        existing_user = cursor.fetchone()

        if existing_user:

            cursor.close()
            conn.close()
            return render_template("userRegistration.html",error="Username already exists.")

        cursor.execute("""SELECT id FROM users WHERE email = %s """,(email,) )
        existing_email = cursor.fetchone()

        if existing_email:

            cursor.close()
            conn.close()
            return render_template("userRegistration.html", error="Email already registered.")

        cursor.execute( """ INSERT INTO users (username, email, password) VALUES (%s, %s, %s) """,(username,email,password))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect("/userLogin")
    return render_template("userRegistration.html")


@app.route("/userDashboard")
def userDashboard():

    if "user_id" not in session:
        return redirect("/userLogin")

    return render_template("userDashboard.html", username=session["username"])

@app.route("/userProfile")
def userProfile():

    if "user_id" not in session:
        return redirect("/userLogin")

    user = get_user()
    return render_template( "userProfile.html",user=user)

@app.route("/updateProfile", methods=["POST"])
def updateProfile():

    if "user_id" not in session:
        return redirect("/userLogin")

    email = request.form.get("email","").strip()
    user = get_user()

    if not email:
        return render_template( "userProfile.html",user=user,error="Email is required.")

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute( """SELECT id FROM users WHERE email = %s AND id != %s """,(email,session["user_id"]))
    existing_email = cursor.fetchone()

    if existing_email:
        cursor.close()
        conn.close()
        return render_template( "userProfile.html", user=user,error="This email is already registered.")

    cursor.execute(""" UPDATE users SET email = %s WHERE id = %s """,( email, session["user_id"]))
    conn.commit()
    cursor.close()
    conn.close()
    user = get_user()
    return render_template("userProfile.html", user=user,success="Email updated successfully.")

@app.route("/changePassword", methods=["POST"])
def changePassword():

    if "user_id" not in session:
        return redirect("/userLogin")

    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")
    user = get_user()

    if (
        not current_password
        or not new_password
        or not confirm_password
    ):
        return render_template("userProfile.html",user=user,error="All password fields are required.")

    if new_password != confirm_password:
        return render_template("userProfile.html",user=user,error="New passwords do not match.")

    if len(new_password) < 5:
        return render_template("userProfile.html",user=user,error="New password must be at least 5 characters.")

    if user["password"] != current_password:
        return render_template("userProfile.html", user=user, error="Current password is incorrect." )

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""UPDATE users SET password = %s WHERE id = %s """,(new_password, session["user_id"]))
    conn.commit()
    cursor.close()
    conn.close()
    user = get_user()
    return render_template("userProfile.html", user=user, success="Password changed successfully. You can now login with your new password.")

@app.route("/submitTicket", methods=["POST"])
def submitTicket():

    if "user_id" not in session:
        return redirect("/userLogin")

    subject = request.form.get("subject", "").strip()
    description = request.form.get( "description","").strip()
    priority = request.form.get("priority","").strip()

    if (
        not subject
        or not description
        or not priority
    ):
        return redirect("/userDashboard")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(""" INSERT INTO tickets (username,subject,description,priority,status) VALUES( %s, %s, %s, %s, %s)""",
        (session["username"], subject, description, priority, "Pending"))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect("/userDashboard")

@app.route("/ticketStatus")
def ticketStatus():

    if "user_id" not in session:
        return redirect("/userLogin")

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""SELECT * FROM tickets WHERE username = %s ORDER BY id DESC """,(session["username"],))
    tickets = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("ticketStatus.html", tickets=tickets)

@app.route("/userLogout")
def userLogout():
    session.clear()
    return redirect("/userLogin")

@app.route("/adminLogin", methods=["GET", "POST"])
def adminLogin():

    if request.method == "POST":
        username = request.form.get( "username","").strip()
        password = request.form.get("password","")

        if username == "admin" and password == "12345":
            session["admin_logged_in"] = True
            session["admin_username"] = "admin"
            return redirect("/adminDashboard")
        return render_template("adminLogin.html",error="Invalid admin username or password.")
    return render_template("adminLogin.html")

@app.route("/adminDashboard")
def adminDashboard():

    if not session.get("admin_logged_in"):
        return redirect("/adminLogin")

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(""" SELECT * FROM tickets ORDER BY id DESC """)
    tickets = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template( "adminDashboard.html", tickets=tickets)

@app.route("/updateTicketStatus/<int:ticket_id>", methods=["POST"])
def updateTicketStatus(ticket_id):

    if not session.get("admin_logged_in"):
        return redirect("/adminLogin")

    status = request.form.get("status", "").strip()
    allowed_statuses = ["Pending","In Progress","Resolved","Closed"]

    if status not in allowed_statuses:
        return redirect("/adminDashboard")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(""" UPDATE tickets SET status = %s WHERE id = %s """,(status,ticket_id))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect("/adminDashboard")

@app.route("/deleteTicket/<int:ticket_id>",methods=["POST"])
def deleteTicket(ticket_id):
    if not session.get("admin_logged_in"):
        return redirect("/adminLogin")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""DELETE FROM tickets WHERE id = %s""",(ticket_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect("/adminDashboard")

@app.route("/adminLogout")
def adminLogout():
    session.pop( "admin_logged_in",None)
    session.pop("admin_username", None)
    return redirect("/adminLogin")

if __name__ == "__main__":
    init_db()
    app.run(debug=True)