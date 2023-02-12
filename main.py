import coloredlogs, logging

coloredlogs.install(level=logging.INFO)

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


LIMIT_BY_TRANSFER_COUNT = 300
UNHIDE_SMALL_TRANSACTIONS = True
MIN_TRANSFER_AMOUNT = 0.0001
MAX_SCAN_DEPTH = 2


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


def get_transfers_url(address: str) -> str:
    return f"https://tronscan.org/#/address/{address}/transfers"


def wait_untill_table_is_filled(driver):
    logging.info("Waiting for tables to get filled...")

    WebDriverWait(driver, 60).until(
        EC.presence_of_element_located(
            (By.CLASS_NAME, "ant-table-row.ant-table-row-level-0")
        )
    )
    sleep(3)
    driver.implicitly_wait(3)

    logging.info("Table got filled.")


def get_transfers(address: str) -> List[Transfer]:
    logging.info(f"Getting transfers for <{address}>...")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )

    logging.info("Session created.")

    url = get_transfers_url(address)
    driver.get(url)

    transfers: List[Transfer] = []
    try:
        wait_untill_table_is_filled(driver)

        # unhide small transfers
        if UNHIDE_SMALL_TRANSACTIONS == True:
            # check if the hide button has already been disabled
            checked = driver.find_element(
                By.XPATH,
                "//button[@class='ant-switch ant-switch-small hiden-scam-switch tron-mr-8px ant-switch-checked']",
            )
            if checked:
                logging.info("Enableing small transactions...")

                # toggle the button
                checked.click()
                wait_untill_table_is_filled(driver)

        # total number of transfers for this address
        total_transfers = int(
            driver.find_element(By.XPATH, "//div[@class='address-txn tron-mr-4px']")
            .find_element(By.XPATH, "//span[@class='color101010']")
            .text
        )
        logging.info(f"Total transfers found for <{address}> is {total_transfers}.")

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
                        address_parent = address
                        address_from = (
                            row.text.replace(",", "").split("\n")[6]
                            + row.text.replace(",", "").split("\n")[7]
                        )
                        address_to = (
                            row.text.replace(",", "").split("\n")[9]
                            + row.text.replace(",", "").split("\n")[10]
                        )
                        amount = float(row.text.replace(",", "").split("\n")[3])
                        age = row.text.replace(",", "").split("\n")[5]
                        is_outgoing = row.text.replace(",", "").split("\n")[8] == "Out"

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
                        logging.info("Switching to the next page...")

                        next_page_lable.click()
                        current_page += 1

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
                        logging.info(f"Switched to the next page ({current_page}).")

                    else:
                        # there is no next page
                        logging.info(f"Reach to the ending page of this address.")
                        break

            else:
                logging.warning(f"No transfers found for address <{address}>")

        else:
            logging.warn(
                f"Address <{address}> transfers <{total_transfers}>, exceeds the limit <{LIMIT_BY_TRANSFER_COUNT}>."
            )

    finally:
        driver.quit()
        logging.info("Session closed.")
        return transfers


def get_rec_transfers(address: str, transfers: List[Transfer], depth=0):
    new_transfers = get_transfers(address)
    transfers.extend(new_transfers)

    for nt in new_transfers:
        if nt.is_outgoing:
            if nt.address_to not in [t.address_parent for t in transfers]:
                if depth <= MAX_SCAN_DEPTH:
                    depth += 1
                    get_rec_transfers(nt.address_to, transfers, depth)
                else:
                    logging.info(
                        f"{nt.address_to} hit MAX_SCAN_DEPTH <{MAX_SCAN_DEPTH}> and won't be included."
                    )
            else:
                logging.info(f"No more new transfers for <{nt.address_to}>.")

    return


if __name__ == "__main__":
    final_set_of_transfers: List[Transfer] = []

    starting_address = "TTVQUuYxDZCnFcmju8k8zNJEaBWiR1z6tM"  # input("Enter the starting tron address: ")

    get_rec_transfers(address=starting_address, transfers=final_set_of_transfers)

    df = pd.DataFrame.from_records(
        [transfer.__dict__ for transfer in final_set_of_transfers]
    )

    # save trasfers to csv file
    logging.info("Saving transfers to file...")
    df.to_csv("transfers.csv")

    logging.info("CSV file created.")
