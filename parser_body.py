import os

import requests, time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from typing import Dict

load_dotenv()
LOGIN = os.getenv('LOGIN')
PASSWORD = os.getenv('PASSWORD')
HOOK = os.getenv('HOOK')
AUTH_URL = os.getenv('AUTH_URL')
DRIVER_PATH = os.getenv('DRIVER_PATH')

## TODO
# SHOULD BE REQUESTED FROM SERVER
ICorsi_ids = [
    'https://www.icorsi.ch/course/view.php?id=10479',
    'https://www.icorsi.ch/course/view.php?id=19782',
    'https://www.icorsi.ch/course/view.php?id=19984',
    'https://www.icorsi.ch/course/view.php?id=10481',
    'https://www.icorsi.ch/course/view.php?id=19892',
    'https://www.icorsi.ch/course/view.php?id=19763',
    'https://www.icorsi.ch/course/view.php?id=10488'
]


def drivers_init() -> webdriver:
    """
    Initializes a headless Chrome WebDriver.

    This function sets up Chrome options to run the browser in headless mode (without a graphical user interface)
    and creates a Chrome WebDriver instance using the specified driver path.

    :return: A Chrome WebDriver instance with headless options configured.
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    # chrome_options.add_argument("--disable-extensions")
    # chrome_options.add_argument("--disable-gpu")
    # chrome_options.add_argument("--no-sandbox") # linux only
    service = webdriver.ChromeService(executable_path=DRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


# Constants for fixed sleep times


def post_request(data):
    """
    :param data: Dictionary containing the payload to be sent in the POST request
    :return: Response object resulting from the POST request
    """
    response = requests.post(HOOK, json=data)
    return response


def navigate_and_login(driver: webdriver = drivers_init(), url: str = AUTH_URL, login: str = LOGIN,
                       password: str = PASSWORD):
    """
    :param driver: WebDriver instance used to interact with the browser.
    :param url: URL to navigate to for login.
    :param login: User login identifier (e.g., username or email).
    :param password: User password.
    :return: None
    """
    short_delay = 3
    post_login_delay = 30

    driver.get(url)
    print('Navigated to URL')
    time.sleep(short_delay)

    def enter_text_and_submit(field_name, field_value, submit_selector = 'input[type="submit" i]'):
        driver.find_element(by=By.NAME, value=field_name).send_keys(field_value)
        driver.find_element(by=By.CSS_SELECTOR, value=submit_selector).click()
        print(f'Submitted {field_name}')
        time.sleep(short_delay)

    enter_text_and_submit('loginfmt', login)
    enter_text_and_submit('passwd', password)

    print(driver.find_element(by=By.XPATH,
                              value='/html/body/div/form[1]/div/div/div[2]/div[1]/div/div/div/div/div/div[2]/div[2]/div/div[2]/div/div[3]/div/div/div').text)
    time.sleep(post_login_delay)
    driver.find_element(by=By.CSS_SELECTOR, value='input[type="submit" i]').click()
    time.sleep(short_delay)


requests.post('http://127.0.0.1:8000/webhook', json={'data': 'Logging in to ICorsi'})
navigate_and_login()
requests.post('http://127.0.0.1:8000/webhook', json={'data': 'Logined succesfully'})


def get_course_items() -> Dict[str, set]:
    res = dict()
    for i in ICorsi_ids:
        formatted = ICorsi_url.format(i=i)
        driver.get(formatted)
        time.sleep(1)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        name = soup.find('div', {'class': 'page-header-headings'}).text
        res[name] = set()

        items = soup.find_all('li', {'data-for': 'cmitem'})
        for items in items:
            if t := items.find('span', {'class': 'instancename'}):
                res[name].add(t.find(string=True, recursive=False).strip())
    return res


course_items_prev = get_course_items()
while True:
    time.sleep(23)

    course_items = get_course_items()
    print(
        '---------------------------------------------CHECKING FOR CHANGES---------------------------------------------')
    message = ''
    for key in course_items_prev.keys():
        added = course_items[key] - course_items_prev[key]
        removed = course_items_prev[key] - course_items[key]
        if len(added) != 0 or len(removed) != 0:
            message += f'FOR "{key}":\n'

            if len(added) != 0:
                message += '\tADDED:\n'
                for i in added:
                    message += f'\t{i}\n'

            if len(removed) != 0:
                message += '\tREMOVED:\n'
                for i in removed:
                    message += f'\t{i}\n'
    if message != '':
        requests.post('http://127.0.0.1:8000/webhook', json={'data': message})
    course_items_prev = course_items
