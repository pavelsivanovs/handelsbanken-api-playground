"""
    README

    Before running the code, make sure you create a .env file and set a variable **HANDELSBANKEN_CLIENT_ID** to be equal
    to the Client ID of your Handelsbanken Application.

    :author: Pavels Ivanovs <pavelsivanovs.lv@gmail.com>
"""

import csv
import os
import re

from dotenv import load_dotenv
import requests


class Handelsbanken:
    """
    Class providing easy interface to Handlesbanken API for retrieving accounts and accounts' transactions.
    """
    BASE_URL = 'https://sandbox.handelsbanken.com/openbanking'
    REDIRECT_URI = 'https://example.com'
    DEFAULT_HEADERS = {
        'accept': 'application/json',
        'connection': 'keep-alive'
    }

    def __init__(self, client_id):
        """
        Class providing easy interface to Handlesbanken API for retrieving accounts and accounts' transactions.

        :param client_id: Client ID of your registered Handelsbanken application.
        """
        self.client_id = client_id
        self.access_token = None
        self.consent_id = None
        self.authorization_endpoint = None
        self.authorization_code = None
        self.auth_access_token = None
        self.refresh_token = None

        self.authorize()

    @property
    def ais_endpoint_headers(self):
        return {
            **self.DEFAULT_HEADERS,
            'x-ibm-client-id': self.client_id,
            'authorization': f'Bearer {self.auth_access_token}',
            'tpp-request-id': 'test',
            'tpp-transaction-id': 'test'
        }

    def authorize(self):
        """
        Runs all the methods required for making calls to Handelsbanken API endpoints.
        """
        self.request_ccg_token()
        self.initiate_consent()
        self.initiate_authorization()
        self.request_acg_token()

    def request_ccg_token(self):
        """
        Starting authorization process by requiring a Client Credentials Grant (CCG).
        Retrieved CCG token is later used to call the POST /consents endpoint for initiating end user consent.
        """
        headers = {
            **self.DEFAULT_HEADERS,
            'content-type': 'application/x-www-form-urlencoded'
        }

        payload = {
            'grant_type': 'client_credentials',
            'scope': 'AIS',
            'client_id': self.client_id
        }

        r = requests.post(f'{self.BASE_URL}/oauth2/token/1.0',
                          headers=headers,
                          data=payload)
        json_body = r.json()
        self.access_token = json_body['access_token']

    def initiate_consent(self):
        """
        Initiating end user consent. Retrieved consent ID is used later when the end user (PSU) signs the consent.
        """
        headers = {
            **self.DEFAULT_HEADERS,
            'authorization': f'Bearer {self.access_token}',
            'content-type': 'application/json',
            'country': 'GB',
            'x-ibm-client-id': self.client_id,
            'tpp-request-id': 'test',
            'tpp-transaction-id': 'test'
        }

        payload = {
            'access': 'ALL_ACCOUNTS'
        }

        r = requests.post(f'{self.BASE_URL}/psd2/v1/consents',
                          headers=headers,
                          json=payload)
        json_body = r.json()

        self.consent_id = json_body['consentId']

        redirect_methods = filter(
            lambda method: method['scaMethodType'] == 'REDIRECT',
            json_body['scaMethods'])

        for redirect_method in redirect_methods:
            href = redirect_method['_links']['authorization'][0]['href']
            self.authorization_endpoint = href

    def initiate_authorization(self):
        """
        Initiating of authorization of PSU. Retrieved authorization code is later used for retrieving Authorization
        Code Grant (ACG).
        """
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'scope': f'AIS:{self.consent_id}',
            'redirect_uri': self.REDIRECT_URI,
            'state': 'state'
        }

        r = requests.get(f'{self.authorization_endpoint}',
                         headers=self.DEFAULT_HEADERS,
                         params=params)
        pattern = re.compile('var authorizationCode = \'(.*?)\';')
        self.authorization_code = pattern.search(r.text).group(1)

    def request_acg_token(self):
        """
        Retrieving ACG, which is required for sending requests to Handelsbanken's API endpoints.
        """
        headers = {
            **self.DEFAULT_HEADERS,
            'content-type': 'application/x-www-form-urlencoded'
        }

        payload = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'scope': f'AIS:{self.consent_id}',
            'code': self.authorization_code,
            'redirect_uri': self.REDIRECT_URI
        }

        r = requests.post(f'{self.BASE_URL}/redirect/oauth2/token/1.0',
                          headers=headers,
                          data=payload)
        json_body = r.json()
        self.refresh_token = json_body['refresh_token']
        self.auth_access_token = json_body['access_token']

    def get_accounts(self) -> dict:
        """
        Retrieving the list of available accounts for a customer via sending a request to Account Information API.

        :return: dictionary representing info about accounts.
        """
        headers = self.ais_endpoint_headers

        r = requests.get(f'{self.BASE_URL}/psd2/v2/accounts',
                         headers=headers)
        return r.json()['accounts']

    def get_transactions(self, account_id) -> dict:
        """
        Retrieving the list of transactions for a supplied customer ID via sending a request to Account Information API.

        :param account_id: ID of an account.
        :return: dictionary representing all transactions of an account.
        """
        headers = self.ais_endpoint_headers

        r = requests.get(f'{self.BASE_URL}/psd2/v2/accounts/{account_id}/transactions',
                         headers=headers)
        return r.json()['transactions']


def process_amount_key(amount: dict) -> str:
    """
    Processes the `amount` dictionary to string.

    :return: Processed string.
    """
    return f"{amount['currency']} {amount['content']}"


def prepare_transaction(transaction: dict) -> list:
    """
    Prepares a transaction object to be written into the CSV file.

    :param transaction: transaction object.
    :return: A list of transaction fields ready to be written into the CSV file.
    """
    transaction_keys = ['status', 'amount', 'ledgerDate', 'transactionDate', 'creditDebit', 'remittanceInformation',
                        'balance']
    received_transaction_keys = transaction.keys()
    csv_ready_transaction = []

    for key in transaction_keys:
        if key in received_transaction_keys:
            if key == 'amount':
                csv_ready_transaction.append(process_amount_key(transaction['amount']))
            elif key == 'balance':
                tb = transaction['balance']
                balance = f"{tb['balanceType']}: {process_amount_key(tb['amount'])}"
                csv_ready_transaction.append(balance)
            else:
                csv_ready_transaction.append(transaction[key])
        else:
            csv_ready_transaction.append('')

    return csv_ready_transaction


if __name__ == '__main__':
    load_dotenv()
    handelsbanken_client_id = os.environ['HANDELSBANKEN_CLIENT_ID']

    bank = Handelsbanken(handelsbanken_client_id)
    bank_accounts = bank.get_accounts()

    with open('transactions.csv', mode='w', encoding='utf8') as file:
        writer = csv.writer(file)
        writer.writerow(['Account ID', 'Owner Name', 'Status', 'Amount', 'Ledger Date', 'Transaction Date',
                         'Credit/Debit', 'Remittance Information', 'Balance'])

        for account in bank_accounts:
            transactions = bank.get_transactions(account['accountId'])

            for trans in transactions:
                trans_csv = prepare_transaction(trans)
                row_fields = [account['accountId'], account['ownerName']] + trans_csv

                writer.writerow(row_fields)
