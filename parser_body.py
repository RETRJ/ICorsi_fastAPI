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
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-gpu")
    # chrome_options.add_argument("--no-sandbox") # linux only
    service = webdriver.ChromeService(executable_path=DRIVER_PATH)
    return webdriver.Chrome(service=service, options=chrome_options)


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


def post_request(data, url = HOOK):
    """
    :param data: The payload to be sent in the POST request. It should be a dictionary representing the JSON body.
    :param url: The URL to which the POST request will be sent. Defaults to the value of the HOOK variable.
    :return: The response object returned by the requests.post call, containing the server's response to the HTTP request.
    """
    response = requests.post(url, json=data)
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

    async def get_course_items() -> Dict[str, list[Dict[str, str]]]:
        """
        Fetches course items from a list of URLs and parses the content to extract specific items.

        :return: Dictionary where keys are course names and values are sets of extracted item names.
        """
        res = dict()
        for url in courses:
            driver.get(url['url'])
            WebDriverWait(driver, 30).until(EC.visibility_of_element_located((By.CLASS_NAME, 'page-header-headings')))
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            res[url['name']] = list()

            items = soup.find_all('li', {'data-for': 'cmitem'})
            for item in items:
                if t := item.find('span', {'class': 'instancename'}):
                    item_name = t.find(string=True, recursive=False).strip()
                    if typ := t.find('span', {'class': 'accesshide '}):
                        item_type = typ.find(string=True, recursive=False).strip()
                    else:
                        item_type = 'Link'
                else:
                    continue
                link = item.find('a')['href']
                res[url['name']].append(
                    {'name': item_name, 'type': item_type, 'link': link}
                )

        return res

    def find_difference(list1: list[Dict[str, str]], list2: list[Dict[str, str]]) -> tuple[list[Dict[str, str]], list[Dict[str, str]]] :
        """
        :param list1: First list of dictionaries to compare.
        :param list2: Second list of dictionaries to compare.
        :return: A tuple containing two lists of dictionaries - the first list contains the dictionaries that are in list2 but not in list1, and the second list contains the dictionaries that are in list1 but not in list2.
        """
        set1 = {frozenset(d.items()) for d in list1}
        set2 = {frozenset(d.items()) for d in list2}

        add = [dict(items) for items in (set2 - set1)]
        rem = [dict(items) for items in (set1 - set2)]

        return add, rem

    course_items_prev = await get_course_items()
    #course_items_prev = dict()
    while True:
        print(course_items_prev)
        await asyncio.sleep(interval)

        course_items = await get_course_items()
        print(
            f'parsing {courses}')
        message = dict()
        for key in course_items_prev.keys():
            added, removed = find_difference(course_items[key], course_items_prev[key])
            if added or removed:
                message[key] = {'added': added, 'removed': removed}
        if message:
            post_request(data={'data': message})
        course_items_prev = course_items
