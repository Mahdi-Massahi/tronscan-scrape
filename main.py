import logging

import pandas as pd
from time import sleep

from typing import List

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


options = Options()
options.add_argument("start-maximized")
options.add_experimental_option("detach", True)
driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()), options=options
)

LIMIT_BY_TRANSFER_COUNT = 300
UNHIDE_SMALL_TRANSACTIONS = True


class Transfer:
    address_parent: str
    address_from: str
    address_to: str
    amount: float
    age: str
    is_outgoing: bool

    def __init__(
        self,
        address_parent: str,
        address_from: str,
        address_to: str,
        amount: float,
        age: str,
        is_outgoing: bool,
    ) -> None:
        self.address_parent = address_parent
        self.address_from = address_from
        self.address_to = address_to
        self.amount = amount
        self.age = age
        self.is_outgoing = is_outgoing


starting_address = (
    "TTVQUuYxDZCnFcmju8k8zNJEaBWiR1z6tM"  # input("Enter the starting tron address: ")
)


def get_transfers_url(address: str) -> str:
    return f"https://tronscan.org/#/address/{address}/transfers"


def get_address_from(content: str) -> str:
    address = (
        content.find_element(
            By.XPATH,
            "//td[@class='ant-table-cell ant_table address_max_width from_address']",
        )
        .find_element(By.XPATH, "//div[@class='ellipsis_box_start']")
        .text
        + content.find_element(
            By.XPATH,
            "//td[@class='ant-table-cell ant_table address_max_width from_address']",
        )
        .find_element(By.XPATH, "//div[@class='ellipsis_box_end']")
        .text
    )
    return address


def get_address_to(content: str) -> str:
    address = (
        content.find_element(
            By.XPATH,
            "//td[@class='ant-table-cell ant_table address_max_width to_address']",
        )
        .find_element(By.XPATH, "//div[@class='ellipsis_box_start']")
        .text
        + content.find_element(
            By.XPATH,
            "//td[@class='ant-table-cell ant_table address_max_width to_address']",
        )
        .find_element(By.XPATH, "//div[@class='ellipsis_box_end']")
        .text
    )
    return address


def get_amount(content: str) -> float:
    amount = float(
        content.find_element(
            By.XPATH, "//span[@class='text-truncate token-amount']"
        ).text
    )
    return amount


def get_age(content: str) -> str:
    age = content.find_element(By.XPATH, "//div[@class='token_black table_pos']").text
    return age


def get_is_outgoing(content: str) -> bool:
    is_outgoing = (
        False
        if content.find_element(By.XPATH, "//div[@class='in-icon to-icon']").text
        == "In"
        else True
    )
    return is_outgoing


transfers: List[Transfer] = []

current_address = starting_address
url = get_transfers_url(starting_address)
driver.get(url)

try:
    # wait until page loads
    WebDriverWait(driver, 60).until(
        EC.presence_of_element_located(
            (By.CLASS_NAME, "ant-table-row.ant-table-row-level-0")
        )
    )

    # # scrap info
    # soup = BeautifulSoup(driver.page_source)

    # unhide small transfers
    if UNHIDE_SMALL_TRANSACTIONS == True:
        # check if the hide button has already been disabled
        checked = driver.find_element(
            By.XPATH,
            "//button[@class='ant-switch ant-switch-small hiden-scam-switch tron-mr-8px ant-switch-checked']",
        )
        if checked:
            # toggle the button
            checked.click()
            sleep(1)

            # wait until page loads
            WebDriverWait(driver, 60).until(
                EC.presence_of_element_located(
                    (By.CLASS_NAME, "ant-table-row.ant-table-row-level-0")
                )
            )

    # total number of transfers for this address
    total_transfers = int(
        driver.find_element(By.XPATH, "//div[@class='address-txn tron-mr-4px']")
        .find_element(By.XPATH, "//span[@class='color101010']")
        .text
    )

    # include transacions if total transfers satisfies the limit
    if total_transfers < LIMIT_BY_TRANSFER_COUNT:
        if total_transfers > 0:
            # extract the currently available transfers in this page's table
            rows = driver.find_elements(
                By.XPATH, "//tr[@class='ant-table-row ant-table-row-level-0']"
            )
            for row in rows:
                address_parent = current_address
                address_from = get_address_from(row)
                address_to = get_address_to(row)
                amount = get_amount(row)
                age = get_age(row)
                is_outgoing = get_is_outgoing(row)

                transfer = Transfer(
                    address_parent=address_parent,
                    address_from=address_from,
                    address_to=address_to,
                    amount=amount,
                    age=age,
                    is_outgoing=is_outgoing,
                )
                transfers.append(transfer)

            # TODO: next page if exists

        else:
            logging.warn(f"No transfers found for address <{current_address}>")

    else:
        logging.warn(
            f"Address <{current_address}> transfers <{total_transfers}>, exceeds the limit <{LIMIT_BY_TRANSFER_COUNT}>."
        )


finally:
    # save trasfers to csv file
    df = pd.DataFrame.from_records([t.__dict__ for t in transfers])
    df.to_csv("transfers.csv")

    driver.quit()
