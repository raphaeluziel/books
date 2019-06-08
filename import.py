import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# This looks for secret stuff in a .env file
from dotenv import load_dotenv
load_dotenv()

# Check for environment variable
if not os.getenv("BOOKSDB_URL"):
    raise RuntimeError("BOOKSDB_URL is not set")

# Setup database connection
engine = create_engine(os.getenv("BOOKSDB_URL"))
db = scoped_session(sessionmaker(bind=engine))

def main():
    f = open("books.csv")
    reader = csv.reader(f)
    headers = next(reader)
    for isbn, title, author, year in reader:
        db.execute('INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)',
        {'isbn':isbn, 'title':title, 'author':author, 'year':year})
        print('Added {} to database'.format({ title })) # for older python versions
    db.commit()

if __name__ == "__main__":
    main()
