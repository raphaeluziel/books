import os
import datetime
import json
import requests

from flask import Flask, render_template, request, redirect, session, url_for
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash

# This looks for secret stuff in a .env file
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

# Check for environment variable
if not os.getenv("BOOKSDB_URL"):
    raise RuntimeError("BOOKSDB_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Setup database connection
engine = create_engine(os.getenv("BOOKSDB_URL"))
db = scoped_session(sessionmaker(bind=engine))

@app.route("/")
def index():

    """Render home page"""

    return render_template("index.html")


@app.route("/login", methods=["POST"])
def login():

    """Log user in"""

    # Forget any user # ID:
    session.clear()

    # Ensure user sent username and password
    if not request.form.get("username"):
        message = "you must enter a username"
        return render_template("index.html", message=message)
    if not request.form.get("password"):
        message = "please enter your password"
        return render_template("index.html", message=message)

    # Query database for user
    user = db.execute("SELECT * FROM users WHERE username = :username",
        {"username":request.form.get("username")}).fetchone()

    # Is username in database?
    if not user:
        message = "username does not exist"
        return  render_template("index.html", message=message)

    # Does password match username?
    if not check_password_hash(user.hash, request.form.get("password")):
        message = "password does not match username"
        return  render_template("index.html", message=message)

    # Remember user who logged in
    session["userid"] = user.id

    # Begin searching for books
    return redirect("/search")


@app.route("/logout")
def logout():

    """Log user out"""

    # Forget user # ID:
    session.clear()

    # Send user back to home page
    return redirect("/")


@app.route("/register", methods=["POST"])
def register():

    """Register a new user"""

    # Ensure user filled out form with all required information
    if not request.form.get("name"):
        message = "Please enter your full name"
        return render_template("index.html", message=message)
    if not request.form.get("username"):
        message = "Please choose a username"
        return render_template("index.html", message=message)
    if not request.form.get("password"):
        message = "please enter a password"
        return render_template("index.html", message=message)
    if not request.form.get("email"):
        message = "An email is required in order to register"
        return render_template("index.html", message=message)

    # Encrypt password
    hash = generate_password_hash(request.form.get("password"))

    # Add user to database, unless user already exists
    try:
        db.execute("INSERT INTO users (name, username, email, age, hash) VALUES (:name, :username, :email, :age, :hash)",
            {"name":request.form.get("name"), "username":request.form.get("username"),
            "email":request.form.get("email"), "age":request.form.get("age") or -1, "hash":hash})
        db.commit()
    except:
        message = "Username and/or email already exists"
        return render_template("index.html", message=message)

    # Log user in automatically after registering
    user = db.execute("SELECT * FROM users WHERE username = :username", {"username": request.form.get("username")}).fetchone()
    session["userid"] = user.id

    # All is good, let user start searching for books
    return redirect('/search')

@app.route("/search", methods=["GET", "POST"])
def search():

    """ Search for Book"""

    # User reached page via get (clicked a link)
    if request.method == "GET":

        # Is user logged in?
        try:
            session["userid"]
            user = db.execute("SELECT * FROM users WHERE id = :id", {"id": session["userid"]}).fetchone()
            return render_template("search.html", user=user)

        # No, no record of user being logged in
        except:
            message = "You must log in to search books"
            return render_template("index.html", message=message)

    # User reached page by submitting a form to search for books
    if request.method == "POST":

        # Get user information to send back to the search page
        user = db.execute("SELECT * FROM users WHERE id = :id", {"id": session["userid"]}).fetchone()

        # Get isbn/title/author search from form if user chose to search by these
        if request.form.get("search"):

            # Format search string for ILIKE queries
            search = "%" + str(request.form.get("search")) + "%"

            # Search for books with isbn, title, or author with search term within it
            books = db.execute("SELECT * FROM books WHERE isbn ILIKE :search OR title ILIKE :search OR author ILIKE :search ORDER BY year DESC",
                {"search":search}).fetchall()

        # Get year from form if user included a year to search by
        if request.form.get("year"):

            # Convert year into an integer
            year = int(request.form.get("year"))

            # Search books by year
            books = db.execute("SELECT * FROM books WHERE year = :year ORDER BY year DESC",
                {"year":year}).fetchall()

        # If user included both isbn/title/author AND a year, search books that meet both criteria
        if request.form.get("search") and request.form.get("year"):
            books = db.execute("SELECT * FROM books WHERE year = :year AND (isbn ILIKE :search OR title ILIKE :search OR author ILIKE :search) ORDER BY year DESC",
            {"search":search, "year":year}).fetchall()

        # If book is not in database, send error message
        if len(books) < 1:
            return render_template("search.html", message='Book Not Found in Database', user=user)


        if not request.form.get("search") and not request.form.get("year"):
            message = "Please type in a query"
            return render_template("search.html", message=message, user=None)

        # Send user to search page, but this time with list of books with links
        return render_template("search.html", books=books, user=user)

@app.route("/search/<int:book_id>", methods=["GET", "POST"])
def book(book_id):

    """Book details page"""

    # User reached page via get (clicked a link)
    if request.method == "GET":

        # Is user logged in? If not send user to login page
        try:
            session["userid"]
        except:
            message = "You must log in to search books"
            return render_template("index.html", message=message)

    # Query books based on book_id sent from link in search page
    book = db.execute("SELECT * FROM books WHERE id = :id", {"id": book_id}).fetchone()
    # Get user information from session
    user = db.execute("SELECT * FROM users WHERE id = :id", {"id": session["userid"]}).fetchone()

    # Obtain review data from Goodreads
    payload = {"key": "j4keFTedeDmmZ6Zu9Ondmg", "isbns": book.isbn}
    GRreviews = requests.get("https://www.goodreads.com/book/review_counts.json", params=payload)

    # Join users table with reviews table and search for all reviews of that book
    reviews = db.execute("SELECT * FROM reviews JOIN users ON users.id = reviews.userid WHERE bookid = :bookid ORDER BY posted DESC", {"bookid": book_id}).fetchall()

    # If user submits a review, insert it into the database
    if request.form.get("review"):

        # Check if user has already reviewed the book, and if so, update the review, otherwise insert the review
        # Using the on conflict on constraint UC_reviews do update set to update if the review causes a unique conflict
        db.execute("INSERT INTO reviews (bookid, userid, review, rating) VALUES (:bookid, :userid, :review, :rating) ON CONFLICT ON CONSTRAINT UC_reviews DO UPDATE SET review=:review, rating=:rating, posted=CURRENT_DATE", {"bookid": book_id, "userid":session["userid"], "review":request.form.get("review"), "rating":int(request.form.get("rating"))})
        db.commit()

        # Then update the review query to reflect new review submission
        reviews = db.execute("SELECT * FROM reviews JOIN users ON users.id = reviews.userid WHERE bookid = :bookid ORDER BY posted DESC", {"bookid": book_id}).fetchall()

    # Render the book detail page with all reviews
    return render_template("book.html", book=book, GRreviews=GRreviews, user=user, reviews=reviews)

@app.route("/api/<string:isbn>", methods=["GET"])
def api(isbn):

    # Find book in my database, if not found return 404 error page
    book = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()
    if not book:
        return render_template("error.html", message="The ISBN number you requested is not in our database.", code="404")

    # If book is found get info from goodreads
    ratings = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": os.getenv("KEY"), "isbns": isbn}).json()

    # Form the api and return it if all goes well
    api = {
        "title":book.title,
        "author":book.author,
        "year":book.year,
        "isbn":book.isbn,
        "review_count": ratings['books'][0]['work_ratings_count'],
        "average_score": ratings['books'][0]['average_rating']
        }
    return json.dumps(api)


if __name__ == "__main__":
    app.run(host='0.0.0.0')
