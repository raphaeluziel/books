# Project 1 - Books

CS50 - Web Programming with Python and JavaScript

The main application is books.py.  The index.html page is where users will log in or register.  Once logged in, users will be taken to the search.html page where they can search for books in the database.  A a list of possible matches will be generated, each with a link to the book.html, where users will be able to see reviews from other users, along with stats from https://www.goodreads.com.  A layout.html page is included as a template, and an error.html page for problems requesting book information from the api.

The books.sql just has the SQL statements I used to create the Postgres tables.  I chose to use psql and the command line to do all the database setup as opposed to Adminer or Heroku.

The working website is at https://books.raphaeluziel.net.  I did not use Heroku.  The books.service, books.raphaeluziel.net and wsgi.py files are the required files I needed to set up the app on a VPS (virtual private server) using Gunicorn and Nginx.  
