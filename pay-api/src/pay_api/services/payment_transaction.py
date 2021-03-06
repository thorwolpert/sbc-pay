# Copyright © 2019 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Service to manage Fee Calculation."""

import urllib.parse
import uuid
from datetime import datetime
from typing import Dict

from flask import current_app

from pay_api.exceptions import BusinessException
from pay_api.factory.payment_system_factory import PaymentSystemFactory
from pay_api.models import PaymentTransaction as PaymentTransactionModel
from pay_api.models import PaymentTransactionSchema
from pay_api.services.base_payment_system import PaymentSystemService
from pay_api.services.invoice import Invoice
from pay_api.services.payment_account import PaymentAccount
from pay_api.services.receipt import Receipt
from pay_api.utils.enums import PaymentSystem, Status
from pay_api.utils.errors import Error

from .invoice import InvoiceModel
from .payment import Payment


class PaymentTransaction:  # pylint: disable=too-many-instance-attributes
    """Service to manage Payment transaction operations."""

    def __init__(self):
        """Return a User Service object."""
        self.__dao = None
        self._id: uuid = None
        self._status_code: str = None
        self._payment_id: int = None
        self._client_system_url: str = None
        self._pay_system_url: str = None
        self._transaction_start_time: datetime = None
        self._transaction_end_time: datetime = None

    @property
    def _dao(self):
        if not self.__dao:
            self.__dao = PaymentTransactionModel()
        return self.__dao

    @_dao.setter
    def _dao(self, value):
        self.__dao = value
        self.id: uuid = self._dao.id
        self.status_code: str = self._dao.status_code
        self.payment_id: int = self._dao.payment_id
        self.client_system_url: str = self._dao.client_system_url
        self.pay_system_url: str = self._dao.pay_system_url
        self.transaction_start_time: datetime = self._dao.transaction_start_time
        self.transaction_end_time: datetime = self._dao.transaction_end_time

    @property
    def id(self):
        """Return the _id."""
        return self._id

    @id.setter
    def id(self, value: uuid):
        """Set the id."""
        self._id = value
        self._dao.id = value

    @property
    def status_code(self):
        """Return the status_code."""
        return self._status_code

    @status_code.setter
    def status_code(self, value: str):
        """Set the payment_id."""
        self._status_code = value
        self._dao.status_code = value

    @property
    def payment_id(self):
        """Return the payment_id."""
        return self._payment_id

    @payment_id.setter
    def payment_id(self, value: int):
        """Set the corp_type_code."""
        self._payment_id = value
        self._dao.payment_id = value

    @property
    def client_system_url(self):
        """Return the client_system_url."""
        return self._client_system_url

    @client_system_url.setter
    def client_system_url(self, value: str):
        """Set the client_system_url."""
        self._client_system_url = value
        self._dao.client_system_url = value

    @property
    def pay_system_url(self):
        """Return the pay_system_url."""
        return self._pay_system_url

    @pay_system_url.setter
    def pay_system_url(self, value: str):
        """Set the account_number."""
        self._pay_system_url = value
        self._dao.pay_system_url = value

    @property
    def transaction_start_time(self):
        """Return the transaction_start_time."""
        return self._transaction_start_time

    @transaction_start_time.setter
    def transaction_start_time(self, value: datetime):
        """Set the transaction_start_time."""
        self._transaction_start_time = value
        self._dao.transaction_start_time = value

    @property
    def transaction_end_time(self):
        """Return the transaction_end_time."""
        return self._transaction_end_time

    @transaction_end_time.setter
    def transaction_end_time(self, value: datetime):
        """Set the transaction_end_time."""
        self._transaction_end_time = value
        self._dao.transaction_end_time = value

    def asdict(self):
        """Return the invoice as a python dict."""
        txn_schema = PaymentTransactionSchema()
        d = txn_schema.dump(self._dao)
        return d

    @staticmethod
    def populate(value):
        """Pouplate the service."""
        transaction: PaymentTransaction = PaymentTransaction()
        transaction._dao = value  # pylint: disable=protected-access
        return transaction

    def save(self):
        """Save the fee schedule information."""
        return self._dao.save()

    def flush(self):
        """Save the information to the DB."""
        return self._dao.flush()

    @staticmethod
    def create(payment_identifier: str, redirect_uri: str):
        """Create transaction record."""
        current_app.logger.debug('<create transaction')
        # Lookup payment record
        payment: Payment = Payment.find_by_id(payment_identifier)

        if not payment.id:
            raise BusinessException(Error.PAY005)
        if payment.payment_status_code == Status.COMPLETED.value:  # Cannot start transaction on completed payment
            raise BusinessException(Error.PAY006)

        # If there are active transactions (status=CREATED), then invalidate all of them and create a new one.
        existing_transactions = PaymentTransactionModel.find_by_payment_id(payment.id)
        if existing_transactions:
            for existing_transaction in existing_transactions:
                if existing_transaction.status_code != Status.CANCELLED.value:
                    existing_transaction.status_code = Status.CANCELLED.value
                    existing_transaction.transaction_end_time = datetime.now()
                    existing_transaction.save()

        transaction = PaymentTransaction()
        transaction.payment_id = payment.id
        transaction.client_system_url = redirect_uri
        transaction.status_code = Status.CREATED.value
        transaction_dao = transaction.flush()
        transaction._dao = transaction_dao  # pylint: disable=protected-access
        transaction.pay_system_url = transaction.build_pay_system_url(payment, transaction.id)
        transaction_dao = transaction.save()

        transaction = PaymentTransaction()
        transaction._dao = transaction_dao  # pylint: disable=protected-access
        current_app.logger.debug('>create transaction')

        return transaction

    @staticmethod
    def build_pay_system_url(payment: Payment, transaction_id: uuid):
        """Build pay system url which will be used to redirect to the payment system."""
        current_app.logger.debug('<build_pay_system_url')
        if payment.payment_system_code == PaymentSystem.PAYBC.value:
            invoice = InvoiceModel.find_by_payment_id(payment.id)

            pay_system_url = current_app.config.get('PAYBC_PORTAL_URL') + '?inv_number={}&pbc_ref_number={}'.format(
                invoice.invoice_number, invoice.reference_number
            )

            pay_web_transaction_url = current_app.config.get('AUTH_WEB_PAY_TRANSACTION_URL')
            return_url = urllib.parse.quote(
                f'{pay_web_transaction_url}/returnpayment/{payment.id}/transaction/{transaction_id}', ''
            )
            pay_system_url += f'&redirect_uri={return_url}'

        current_app.logger.debug('>build_pay_system_url')
        return pay_system_url

    @staticmethod
    def find_by_id(payment_identifier: int, transaction_id: uuid):
        """Find transaction by id."""
        transaction_dao = PaymentTransactionModel.find_by_id_and_payment_id(transaction_id, payment_identifier)
        if not transaction_dao:
            raise BusinessException(Error.PAY008)

        transaction = PaymentTransaction()
        transaction._dao = transaction_dao  # pylint: disable=protected-access

        current_app.logger.debug('>find_by_id')
        return transaction

    @staticmethod
    def find_active_by_payment_id(payment_identifier: int):
        """Find active transaction by id."""
        existing_transactions = PaymentTransactionModel.find_by_payment_id(payment_identifier)
        transaction: PaymentTransaction = None
        if existing_transactions:
            for existing_transaction in existing_transactions:
                if existing_transaction.status_code not in (Status.COMPLETED.value, Status.CANCELLED.value):
                    transaction = existing_transaction

        current_app.logger.debug('>find_active_by_payment_id')
        return transaction

    @staticmethod
    def update_transaction(payment_identifier: int, transaction_id: uuid, receipt_number: str):
        """Update transaction record.

        Does the following:
        1. Find the payment record with the id
        2. Find the invoice record using the payment identifier
        3. Call the pay system service and get the receipt details
        4. Save the receipt record
        5. Change the status of Invoice
        6. Change the status of Payment
        7. Update the transaction record
        """
        transaction_dao: PaymentTransactionModel = PaymentTransactionModel.find_by_id_and_payment_id(
            transaction_id, payment_identifier
        )
        if not transaction_dao:
            raise BusinessException(Error.PAY008)
        if transaction_dao.status_code == Status.COMPLETED.value:
            raise BusinessException(Error.PAY006)

        payment: Payment = Payment.find_by_id(payment_identifier)

        pay_system_service: PaymentSystemService = PaymentSystemFactory.create(
            payment_system=payment.payment_system_code
        )

        invoice = Invoice.find_by_payment_identifier(payment_identifier)

        payment_account = PaymentAccount.find_by_id(invoice.account_id)

        receipt_details = pay_system_service.get_receipt(payment_account, receipt_number, invoice.invoice_number)
        if receipt_details:
            # Find if a receipt exists with same receipt_number for the invoice
            receipt: Receipt = Receipt.find_by_invoice_id_and_receipt_number(invoice.id, receipt_details[0])
            if not receipt.id:
                receipt: Receipt = Receipt()
                receipt.receipt_number = receipt_details[0]
                receipt.receipt_date = receipt_details[1]
                receipt.receipt_amount = receipt_details[2]
                receipt.invoice_id = invoice.id
            else:
                receipt.receipt_date = receipt_details[1]
                receipt.receipt_amount = receipt_details[2]
            # Save receipt details to DB.
            receipt.save()

            invoice.paid = receipt.receipt_amount
            if invoice.paid == invoice.total:
                invoice.invoice_status_code = Status.COMPLETED.value
                payment.payment_status_code = Status.COMPLETED.value
                payment.save()
            elif 0 < invoice.paid < invoice.total:
                invoice.invoice_status_code = Status.PARTIAL.value
            invoice.save()

        transaction_dao.transaction_end_time = datetime.now()
        transaction_dao.status_code = Status.COMPLETED.value
        transaction_dao = transaction_dao.save()

        transaction = PaymentTransaction()
        transaction._dao = transaction_dao  # pylint: disable=protected-access

        current_app.logger.debug('>update_transaction')
        return transaction

    @staticmethod
    def find_by_payment_id(payment_identifier: int):
        """Find all transactions by payment id."""
        transactions_dao = PaymentTransactionModel.find_by_payment_id(payment_identifier)
        data: Dict = {'items': []}
        if transactions_dao:
            for transaction_dao in transactions_dao:
                data['items'].append(PaymentTransaction.populate(transaction_dao).asdict())

        current_app.logger.debug('>find_by_payment_id')
        return data
