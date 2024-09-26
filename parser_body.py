import os

import requests, asyncio
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from typing import Dict, List

load_dotenv()
LOGIN = os.getenv('LOGIN')
PASSWORD = os.getenv('PASSWORD')
HOOK = os.getenv('HOOK')
AUTH_URL = os.getenv('AUTH_URL')
DRIVER_PATH = os.getenv('DRIVER_PATH')


def drivers_init() -> webdriver:
    """
    Initializes and returns a headless Chrome WebDriver instance.

    :return: A Selenium WebDriver instance configured to run in headless mode.
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    # chrome_options.add_argument("--disable-extensions")
    # chrome_options.add_argument("--disable-gpu")
    # chrome_options.add_argument("--no-sandbox") # linux only
    service = webdriver.ChromeService(executable_path=DRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


driver = drivers_init()


def navigate_and_login(url: str = AUTH_URL, login: str = LOGIN, password: str = PASSWORD):
    """
    :param url: The URL to navigate to for authentication.
    :param login: The login credential used for authentication.
    :param password: The password credential used for authentication.
    :return: None
    """
    if driver is None:
        exit(1)

    timeout = 30

    driver.get(url)
    print('Navigated to URL')

    def enter_text_and_submit(field_name, field_value, submit_selector='input[type="submit" i]'):
        WebDriverWait(driver, timeout).until(EC.visibility_of_element_located((By.NAME, field_name)))
        driver.find_element(by=By.NAME, value=field_name).send_keys(field_value)
        driver.find_element(by=By.CSS_SELECTOR, value=submit_selector).click()
        print(f'Submitted {field_name}')

    enter_text_and_submit('loginfmt', login)
    enter_text_and_submit('passwd', password)

    WebDriverWait(driver, timeout).until(EC.visibility_of_element_located((By.XPATH,
                                                                           '/html/body/div/form[1]/div/div/div[2]/div[1]/div/div/div/div/div/div[2]/div[2]/div/div[2]/div/div[3]/div/div/div')))
    print(driver.find_element(by=By.XPATH,
                              value='/html/body/div/form[1]/div/div/div[2]/div[1]/div/div/div/div/div/div[2]/div[2]/div/div[2]/div/div[3]/div/div/div').text)

    WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[type="submit" i]')))
    driver.find_element(by=By.CSS_SELECTOR, value='input[type="submit" i]').click()
    WebDriverWait(driver, timeout).until(EC.url_changes(url))


def post_request(data):
    """
    :param data: Data to be sent in the body of the POST request. This should be in a format that can be serialized to JSON.
    :return: The response object resulting from the POST request.
    """
    response = requests.post(HOOK, json=data)
    return response


courses: List[Dict[str, str]] = list()


async def add_course(url: str):
    """
    :param url: The URL of the course to be added.
    :return: None
    """
    if 'https://www.icorsi.ch/' not in url:
        post_request(data={'data': f'Not "<https://www.icorsi.ch/>"'})
        print(
            f'Failed to add {url}'
        )
        return
    try:
        driver.get(url)
        WebDriverWait(driver, 30).until(EC.visibility_of_element_located((By.CLASS_NAME, 'page-header-headings')))
        if 'enrol' in driver.current_url:
            post_request(data={'data': f'Not allowed'})
            print(
                f'Failed to add {url}'
            )
            return
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        name = soup.find('div', {'class': 'page-header-headings'}).text.strip()
        if name == 'iCorsi':
            post_request(data={'data': f'Not allowed'})
            print(
                f'Failed to add {url}'
            )
            return

        courses.append({'name': name, 'url': url})
        post_request(data={'data': f'Course ["{name}"](<{url}>) added'})
        print(
            f'Course "{name}" added'
        )
    except:
        post_request(data={'data': f'Failed to add [LINK](<{url}>)'})
        print(
            f'Failed to add {url}'
        )


async def parser_worker(interval):
    """
    :param interval: The time interval in seconds that the worker waits between parsing activities.
    """
    post_request(data={'data': 'Logging in to ICorsi'})
    navigate_and_login()
    post_request(data={'data': 'Logined succesfully'})

    async def get_course_items() -> Dict[str, set]:
        """
        Fetches course items from a list of URLs and parses the content to extract specific items.

        :return: Dictionary where keys are course names and values are sets of extracted item names.
        """
        res = dict()
        for url in courses:
            driver.get(url['url'])
            WebDriverWait(driver, 30).until(EC.visibility_of_element_located((By.CLASS_NAME, 'page-header-headings')))
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            res[url['name']] = set()

            items = soup.find_all('li', {'data-for': 'cmitem'})
            for items in items:
                if t := items.find('span', {'class': 'instancename'}):
                    res[url['name']].add(t.find(string=True, recursive=False).strip())
        return res

    course_items_prev = await get_course_items()
    while True:
        await asyncio.sleep(interval)

        course_items = await get_course_items()
        print(
            f'parsing {courses}')
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
            post_request(data={'data': message})
        course_items_prev = course_items
