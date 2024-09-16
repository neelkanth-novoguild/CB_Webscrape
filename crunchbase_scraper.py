import sys
import re
import random
import psycopg2
from bs4 import BeautifulSoup
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QUrl
from PyQt5.QtWebEngineWidgets import QWebEnginePage

BASE_URL = 'https://www.crunchbase.com'

API_KEYS = [
    'api_key_1',
    'api_key_2',
    'api_key_3',
    'api_key_4'
]

companies = []
pages = []


class Page(QWebEnginePage):
    def __init__(self, url):
        self.app = QApplication(sys.argv)
        QWebEnginePage.__init__(self)
        self.html = ''
        self.loadFinished.connect(self._on_load_finished)
        self.load(QUrl(url))
        self.app.exec_()

    def _on_load_finished(self):
        self.html = self.toHtml(self.Callable)

    def Callable(self, html_str):
        self.html = html_str
        self.app.quit()


def get_page(route):
    if not route:
        return None

    try:
        url = f'{BASE_URL}{route}'
        pages.append(Page(url))
        soup = BeautifulSoup(pages[-1].html, 'lxml')
        pages[-1].deleteLater()
    except:
        return None
    else:
        return soup


def format_name(name):
    return name.lower().replace('\n', '').strip().replace('.', '-').replace(' ', '-').replace(':', '-')


def extract_link(element):
    return re.search(r'(https?:\/\/)(www\.)?([a-zA-Z0-9]+(-?[a-zA-Z0-9])*\.)+([a-z]{2,})(\/\S*)?', element).group(0)


def print_green(s):
    print(f'\033[92m{s}\033[0m')


def connect_to_db():
    try:
        connection = psycopg2.connect(
            host="localhost", 
            database="your_database_name",  
            user="your_username",  
            password="your_password"  
        )
        return connection
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        sys.exit(1)


def scrape_data(company_name, connection):
    api_key = random.choice(API_KEYS)
    print_green(f'Using API Key: {api_key}')

    name = format_name(company_name)

    print_green(f'Checking {company_name} alias {name}')

    soup = get_page(f'/organization/{name}?api_key={api_key}')
    if not soup:
        print_green(f'{company_name}, alias {name} gave an error while loading')
        return

    html_links = soup.find_all(
        'a', class_="cb-link component--field-formatter field-type-link layout-row layout-align-start-end ng-star-inserted")
    links = []
    for html in html_links:
        link = extract_link(str(html))
        links.append(link)

    if len(links) == 0:
        print_green(f'{company_name}, alias {name} could not be found')
        return

    website = links[0]
    company_twitter = None
    if 'twitter' in links[-1]:
        company_twitter = links[-1].split('/')[-1]

    html_persons = soup.find_all(
        'div', class_='flex cb-padding-medium-left cb-break-word cb-hyphen')

    ceo = None
    cto = None
    founders = []

    for html_person in html_persons:
        name_link = html_person.find('a')['href']
        position = html_person.find('span')['title']

        if re.search(r'(\s|^)((ceo)|(Chief Executive Officer))(\s|$)', position, re.I):
            ceo = name_link

        if re.search(r'(\s|^)((cto)|(Chief Technical Officer)|(Chief technology officer))(\s|$)', position, re.I):
            cto = name_link

        if re.search(r'founder', position, re.I):
            founders.append(name_link)

    if not ceo and not cto:
        if len(founders) >= 2:
            (ceo, cto) = founders
        elif len(founders) == 1:
            ceo = founders[0]

    ceo_twitter = None
    cto_twitter = None

    for person in (ceo, cto):
        if not person:
            continue

        soup = get_page(person)
        if not soup:
            print(f'Could not find {person}')
            continue

        card = soup.find('mat-card', class_='component--section-layout mat-card')

        person_twitter = re.search(r'twitter.com/([^"]*)"', str(card))
        if not person_twitter:
            print_green(f"{person} doesn't have a twitter account")
            continue

        if person is ceo:
            ceo_twitter = person_twitter.group(1)
        else:
            cto_twitter = person_twitter.group(1)

    with connection.cursor() as cursor:
        insert_query = """
        INSERT INTO found_companies (company_name, website, company_twitter, ceo_twitter, cto_twitter)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (company_name) DO UPDATE SET
            website = EXCLUDED.website,
            company_twitter = EXCLUDED.company_twitter,
            ceo_twitter = EXCLUDED.ceo_twitter,
            cto_twitter = EXCLUDED.cto_twitter;
        """
        cursor.execute(insert_query, (company_name, website, company_twitter, ceo_twitter, cto_twitter))
        connection.commit()


def fetch_company_names_from_db(connection):
    with connection.cursor() as cursor:
        cursor.execute("SELECT company_name FROM company_list")
        companies = cursor.fetchall()
        return [company[0] for company in companies]


if __name__ == "__main__":
    connection = connect_to_db()

    companies = fetch_company_names_from_db(connection)

    for company in companies:
        scrape_data(company, connection)

    connection.close()
