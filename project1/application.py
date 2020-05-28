import os
import simplejson as json
import requests

from flask import Flask, session, render_template, request, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from flask_bcrypt import Bcrypt


app = Flask(__name__)
bcrypt = Bcrypt(app)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"

Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        session["username"] = request.form.get("username")
        session["password"] = request.form.get("password")
        User = db.execute("SELECT * FROM users WHERE username = :username", {"username": session["username"]}).fetchone()

        if (len(session["username"]) > 0 and len(session["password"]) > 0) == False:
            return render_template("error.html", message="Enter all required field")

        if db.execute("SELECT * FROM users WHERE username = :username", {"username": session["username"]}).rowcount == 0:
            return render_template("error.html", message="Please enter a valid username and password")

        if User is None:
            return render_template("error.html", message="Invalid Username or Password.Try to register first.")
        else:
            Upassword = User.password
            if (User.username in session["username"]) and (bcrypt.check_password_hash(Upassword, session["password"])):
                session["id"] = db.execute("SELECT id FROM users WHERE (username = username) AND (password = password)",{"username": User.username, "password": Upassword}).fetchone()
                session["loggedIn"] = True
                return render_template("search.html")
            else:
                return render_template("error.html", message="Invalid Username or Password.")


    else:
        session["loggedIn"] = False
        return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
        if request.method == "POST":
            username = request.form.get("username")
            password = request.form.get("password").encode("utf-8")
            Cpassword = request.form.get("Cpassword").encode("utf-8")

            if (len(username) > 0 and len(password) > 0 and len(Cpassword) > 0) == False:
                return render_template("error.html", message="Enter all required field")

            if Cpassword != password:
                return render_template("error.html", message="Passwords don't match.")

            if db.execute("SELECT * FROM users WHERE username = :username", {"username": username}).rowcount != 0:
                return render_template("error.html", message="Username already taken please try to choose another one")
            else:
                hashed_pw = bcrypt.generate_password_hash(password).decode()
                db.execute("INSERT INTO users (username, password) VALUES (:username, :password)", {"username": username, "password": hashed_pw})
                db.commit()
                return render_template("register.html", status="success", message="You've successfully registered")
        else:
            return render_template("register.html")
@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "POST":
        isbn = request.form.get("isbn")
        title = request.form.get("title").lower()
        author = request.form.get("author").lower()

        if isbn != "":
            session["isbn"] = f"%{isbn}%"
        if title != "":
            session["title"] = f"%{title}%"
        if author != "":
            session["author"] = f"%{author}%"

        if (isbn == "" and title == "" and author == ""):
            return render_template("search.html", status="You have to input at least on field to search")
        else:
            books = db.execute("SELECT * FROM books WHERE isbn LIKE :isbn AND LOWER(title) LIKE :title AND LOWER(author) LIKE :author",
            {"isbn": f"%{isbn}%", "title": f"%{title}%", "author": f"%{author}%"}).fetchall()
            return render_template("results.html", title="Search Results", books=books)
    else:
        return render_template("search.html")
@app.route("/search/<string:isbn>")
def bookDet(isbn):
    if session["loggedIn"]:
        session["book"] = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()
        session["review"] = db.execute("SELECT * FROM reviews where isbn= :isbn", {"isbn": isbn}).fetchall()
        countb = db.execute("SELECT * FROM reviews where isbn= :isbn", {"isbn": isbn}).rowcount

        res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "kJhVhoNaGVDQZTQyizzMg", "isbns": f"{isbn}"})
        bookG = res.json()
        session["average_rating"] = (bookG["books"][0]["average_rating"])
        session["ratings_count"] = (bookG["books"][0]["ratings_count"])
        return render_template("book.html", title=session["book"].title, author=session["book"].author, year=session["book"].year,
        isbn=isbn, rating=session["average_rating"], count=session["ratings_count"], reviews=session["review"], countb=countb)
    else:
        return render_template("login.html")
@app.route("/review/<string:isbn>", methods=["POST"])
def ratedReview(isbn):
    if session["loggedIn"] and request.method == "POST":
        star = request.form.get("rate")
        reviewText = request.form.get("reviewText")
        username = session["username"]
        countb = db.execute("SELECT * FROM reviews where isbn= :isbn", {"isbn": isbn}).rowcount

        session["review"] = db.execute("SELECT * FROM reviews where username= :username AND isbn= :isbn", {"username": username, "isbn": isbn}).fetchone()

        if session["review"] is None:
            db.execute("INSERT INTO reviews (isbn, username, review, rating) VALUES (:isbn, :username, :review, :rating)",
            {"isbn": isbn, "username": username, "review": reviewText, "rating": star})
            db.commit()
            countb = db.execute("SELECT * FROM reviews where isbn= :isbn", {"isbn": isbn}).rowcount
            session["review1"] = db.execute("SELECT * FROM reviews where isbn= :isbn", {"isbn": isbn}).fetchall()
            return render_template("book.html", title=session["book"].title, author=session["book"].author, year=session["book"].year,
            isbn=isbn, rating=session["average_rating"], count=session["ratings_count"], reviews=session["review1"], username=session["username"],
            status="You have successfully reviewed this book.", countb=countb)

        else:
            session["review1"] = db.execute("SELECT * FROM reviews where isbn= :isbn", {"isbn": isbn}).fetchall()
            return render_template("book.html", title=session["book"].title, author=session["book"].author, year=session["book"].year,
            isbn=isbn, rating=session["average_rating"], count=session["ratings_count"], reviews=session["review1"], username=session["username"],
            status1="You have already reviewed this book already.We're sorry but you can't review this book again.", countb=countb)

    else:
        return render_template("login.html")
@app.route("/api/<string:isbn>")
def book_api(isbn):
    bookData = db.execute("SELECT * FROM books where isbn= :isbn", {"isbn": isbn}).fetchone()
    if bookData is None:
        return jsonify({"error": "Isbn number not found"}), 404
    else:
        res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "kJhVhoNaGVDQZTQyizzMg", "isbns": f"{isbn}"})
        bookG = res.json()

        response = {
            "title": bookData.title,
            "author": bookData.author,
            "year": bookData.year,
            "isbn": isbn,
            "review_count": (bookG["books"][0]["ratings_count"]),
            "average_score": (bookG["books"][0]["average_rating"])
        }
        return json.dumps(response)
@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return render_template("logout.html", message="Successfully logged out of bookz.")
