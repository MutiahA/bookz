import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def main():
    db.execute("CREATE TABLE books(isbn VARCHAR PRIMARY KEY,title VARCHAR NOT NULL,author VARCHAR NOT NULL,year INTEGER NOT NULL);")
    db.execute("CREATE TABLE users(id SERIAL PRIMARY KEY,username VARCHAR NOT NULL,password VARCHAR NOT NULL);")
    db.execute("CREATE TABLE reviews(isbn VARCHAR NOT NULL,username VARCHAR NOT NULL,review VARCHAR NOT NULL,rating INTEGER NOT NULL);")

    b = open("books.csv")
    reader = csv.reader(b)
    for isbn, title, author, year in reader:
        db.execute("INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)",
                    {"isbn": isbn, "title": title, "author": author, "year": year})
        print("done")
    db.commit()

if __name__ == "__main__":
    main()
