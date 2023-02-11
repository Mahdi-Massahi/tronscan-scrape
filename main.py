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
MIN_TRANSFER_AMOUNT = 0.0001


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


def wait_untill_table_is_filled(driver):
    WebDriverWait(driver, 60).until(
        EC.presence_of_element_located(
            (By.CLASS_NAME, "ant-table-row.ant-table-row-level-0")
        )
    )
    sleep(3)
    driver.implicitly_wait(3)


transfers: List[Transfer] = []

current_address = starting_address
url = get_transfers_url(starting_address)
driver.get(url)

try:
    wait_untill_table_is_filled(driver)

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
            wait_untill_table_is_filled(driver)

    # total number of transfers for this address
    total_transfers = int(
        driver.find_element(By.XPATH, "//div[@class='address-txn tron-mr-4px']")
        .find_element(By.XPATH, "//span[@class='color101010']")
        .text
    )

    # include transacions if total transfers satisfies the limit
    if total_transfers < LIMIT_BY_TRANSFER_COUNT:
        if total_transfers > 0:
            current_page = 1
            while True:
                # extract the currently available transfers in this page's table
                rows = driver.find_elements(
                    By.XPATH, "//tr[@class='ant-table-row ant-table-row-level-0']"
                )
                for row in rows:
                    address_parent = current_address
                    address_from = get_address_from(row)
                    address_to = get_address_to(row)
                    amount = float(row.text.replace(",", "").split("\n")[3])
                    age = get_age(row)
                    is_outgoing = get_is_outgoing(row)

                    if abs(amount) >= MIN_TRANSFER_AMOUNT:
                        # only include transfers larger than the limit
                        transfer = Transfer(
                            address_parent=address_parent,
                            address_from=address_from,
                            address_to=address_to,
                            amount=abs(amount),
                            age=age,
                            is_outgoing=is_outgoing,
                        )
                        transfers.append(transfer)

                # next page if exists
                next_page_lable = driver.find_element(
                    By.XPATH, "//li[@title='Next Page']"
                )
                if next_page_lable.get_attribute("aria-disabled") == "false":
                    # there is a next page

                    # next_page_button = driver.find_element(
                    #     By.XPATH, "//button[@class='ant-pagination-item-link']"
                    # )
                    next_page_lable.click()
                    current_page += 1
                    # wait_untill_table_is_filled(driver)
                    print(f"Flipping the page to page no {current_page}...")

                    WebDriverWait(driver, 60).until(
                        EC.presence_of_element_located(
                            (
                                By.XPATH,
                                f"//li[@title='{current_page}' and @class='ant-pagination-item ant-pagination-item-{current_page} ant-pagination-item-active']",
                            )
                        )
                    )

                    sleep(3)
                    driver.implicitly_wait(3)
                    print("Page flipped.")

                else:
                    # there is no next page
                    break

        else:
            print(f"No transfers found for address <{current_address}>")

    else:
        print(
            f"Address <{current_address}> transfers <{total_transfers}>, exceeds the limit <{LIMIT_BY_TRANSFER_COUNT}>."
        )


finally:
    # save trasfers to csv file
    df = pd.DataFrame.from_records([t.__dict__ for t in transfers])
    df.to_csv("transfers.csv")

    driver.quit()
