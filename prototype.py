from googlesearch import search
import sys
import webbrowser
import threading
from autocorrect import Speller
import re
import sqlite3
import datetime
import requests
from bs4 import BeautifulSoup
from htmldate import find_date

class GoogleSearcher:
    def __init__(self, cursor):
        self.case_sensitive = False
        self.search_mode = 'OR'
        self.symbols = []
        self.keyword = ''
        self.results = []
        self.thread = None
        self.cursor = cursor

    def display_searches(self):
        count = int(input("\nEnter the total number of search results you want:\n"))
        return count

    def case_sensitive_search(self):
        case_sensitive = input("\nDo you want to perform case sensitive search? (yes/no):\n")
        if case_sensitive.lower() == 'yes':
            self.case_sensitive = True

    def input_search_mode(self):
        self.search_mode = input("\nEnter the search mode: OR, AND, NOT\n").upper()

    def input_symbol_filter(self):
        self.symbols = list(input("\nEnter the symbols to filter out (e.g., @$#):\n"))

    def filter_symbols(self, query):
        return ''.join(i for i in query if not i in self.symbols)

    def input_keyword(self):
        self.keyword = input("\nEnter the keyword for Google Search:\n")

    def execute_search(self):
        count = self.display_searches()
        self.thread = threading.Thread(target=self._search_google, args=(self.keyword, count))
        self.thread.start()
        print("\nGoogle Search performed successfully.")

    def _search_google(self, keyword, count):
        query = self.search_mode.join(keyword.split()) if self.search_mode in ['AND', 'OR'] else keyword.replace('NOT', '-')
        query = self.filter_symbols(query)

        # Create a new connection and cursor within this thread
        connection = sqlite3.connect('search_results.db')
        cursor = connection.cursor()

        results = []
        for result in search(query, stop=count):
            results.append(result)
            if len(results) == count:
                break

        timestamp = datetime.datetime.now().isoformat()
        self.results = [(keyword, url, timestamp, self.get_last_published_date(url)) for url in results]
        for result in self.results:
            cursor.execute('INSERT INTO search_results (keyword, url, timestamp, last_published_date) VALUES (?, ?, ?, ?)', result)
        cursor.connection.commit()  # Commit the changes to the database

    def get_last_published_date(self, url):
        response = requests.get(url)
        html_content = response.content.decode('utf-8')

        # Use htmldate library to find the publication date from the HTML content
        published_date = find_date(html_content)

        return published_date

    def delete_outdated_results(self, threshold):
        print("\nDeleting out-of-date URLs and descriptions from the database...")

        current_date = datetime.datetime.now().date()
        outdated_results = []
        for keyword, url, timestamp, last_published_date in self.results:
            last_published_date_obj = datetime.datetime.strptime(last_published_date, "%Y-%m-%d").date()
            if last_published_date_obj and last_published_date_obj < current_date - datetime.timedelta(days=threshold):
                outdated_results.append(url)

        if outdated_results:
            self.cursor.execute('DELETE FROM search_results WHERE url IN ({})'.format(','.join(['?'] * len(outdated_results))), outdated_results)
            self.cursor.connection.commit()  # Commit the changes to the database

        print("Deletion completed.")

    def show_search_results(self):
        print("\nThe results for the search are available now:\n")
        for i in range(len(self.results)):
            keyword, url, timestamp, last_published_date = self.results[i]
            title = self.get_website_title(url)
            print(f"\nTitle: {title}")
            print(f"URL: {url}")
            print(f"Last Published Date: {last_published_date}")
        threshold = int(input("Enter the threshold (in days) to consider URLs as up-to-date: "))
        self.delete_outdated_results(threshold)
        
    def get_website_title(self, url):
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        title = soup.find('title').text.strip()
        return title

def main():
    conn = sqlite3.connect('search_results.db')  # Connect to the database file (create if it doesn't exist)
    cursor = conn.cursor()  # Create a cursor object to execute SQL queries

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS search_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT,
            url TEXT,
            timestamp TEXT,
            last_published_date TEXT
        )
    ''')

    google_search_handler = GoogleSearcher(cursor)
    print("\n--- Welcome to Cybermining ---\n")
    google_search_handler.case_sensitive_search()
    google_search_handler.input_search_mode()
    google_search_handler.input_symbol_filter()
    google_search_handler.input_keyword()
    google_search_handler.execute_search()
    google_search_handler.thread.join()
    google_search_handler.show_search_results()

if __name__ == '__main__':
    main()
