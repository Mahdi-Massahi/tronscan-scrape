from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from bs4 import BeautifulSoup

options = Options()
options.add_argument("start-maximized")
options.add_experimental_option("detach", True)
driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()), options=options
)


starting_address = (
    "TTVQUuYxDZCnFcmju8k8zNJEaBWiR1z6tM"  # input("Enter the starting tron address: ")
)


def get_transfers_url(address: str) -> str:
    return f"https://tronscan.org/#/address/{address}/transfers"


url = get_transfers_url(starting_address)
driver.get(url)

try:
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CLASS_NAME, "ant-table-cell"))
    )

    soup = BeautifulSoup(driver)

    table = soup.findAll("tr", {"class": "ant-table-row.ant-table-row-level-0"})
    rows = table.find_all

    for row in rows:
        print(row)

finally:
    driver.quit()
