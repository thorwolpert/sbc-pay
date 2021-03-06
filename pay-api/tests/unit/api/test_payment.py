# Copyright © 2019 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests to assure the payments end-point.

Test-Suite to ensure that the /payments endpoint is working as expected.
"""

import json
from datetime import datetime

from pay_api.models import PaymentTransaction
from pay_api.schemas import utils as schema_utils
from pay_api.utils.enums import Role


token_header = {
    'alg': 'RS256',
    'typ': 'JWT',
    'kid': 'sbc-auth-cron-job'
}


def get_claims(role: str = Role.BASIC.value):
    """Return the claim with the role param."""
    claim = {
        'jti': 'a50fafa4-c4d6-4a9b-9e51-1e5e0d102878',
        'exp': 31531718745,
        'iat': 1531718745,
        'iss': 'https://sso-dev.pathfinder.gov.bc.ca/auth/realms/fcf0kpqr',
        'aud': 'sbc-auth-web',
        'sub': '15099883-3c3f-4b4c-a124-a1824d6cba84',
        'typ': 'Bearer',
        'realm_access':
            {
                'roles':
                    [
                        '{}'.format(role)
                    ]
            },
        'preferred_username': 'test'
    }
    return claim


def factory_payment_transaction(
        payment_id: str,
        status_code: str = 'DRAFT',
        client_system_url: str = 'http://google.com/',
        pay_system_url: str = 'http://google.com',
        transaction_start_time: datetime = datetime.now(),
        transaction_end_time: datetime = datetime.now(),
):
    """Factory."""
    return PaymentTransaction(
        payment_id=payment_id,
        status_code=status_code,
        client_system_url=client_system_url,
        pay_system_url=pay_system_url,
        transaction_start_time=transaction_start_time,
        transaction_end_time=transaction_end_time,
    )


def test_payment_creation(session, client, jwt, app):
    """Assert that the endpoint returns 201."""
    token = jwt.create_jwt(get_claims(), token_header)
    headers = {'Authorization': f'Bearer {token}', 'content-type': 'application/json'}
    data = {
        'payment_info': {
            'method_of_payment': 'CC'
        },
        'business_info': {
            'business_identifier': 'CP1234',
            'corp_type': 'CP',
            'business_name': 'ABC Corp',
            'contact_info': {
                'city': 'Victoria',
                'postal_code': 'V8P2P2',
                'province': 'BC',
                'address_line_1': '100 Douglas Street',
                'country': 'CA'
            }
        },
        'filing_info': {
            'filing_types': [
                {
                    'filing_type_code': 'OTADD',
                    'filing_description': 'TEST'
                },
                {
                    'filing_type_code': 'OTANN'
                }
            ]
        }
    }
    rv = client.post(f'/api/v1/payments', data=json.dumps(data), headers=headers)
    assert rv.status_code == 201
    assert rv.json.get('_links') is not None

    assert schema_utils.validate(rv.json, 'payment_response')[0]


def test_payment_incomplete_input(session, client, jwt, app):
    """Assert that the endpoint returns 201."""
    token = jwt.create_jwt(get_claims(), token_header)
    headers = {'Authorization': f'Bearer {token}', 'content-type': 'application/json'}
    data = {
        'payment_info': {
            'method_of_payment': 'CC'
        },
        'business_info': {
            'business_identifier': 'CP1234',
            'corp_type': 'CP',
            'business_name': 'ABC Corp',
            'contact_info': {
                'city': 'Victoria',
                'postal_code': 'V8P2P2',
                'province': 'BC',
                'address_line_1': '100 Douglas Street',
                'country': 'CA'
            }
        }
    }
    rv = client.post(f'/api/v1/payments', data=json.dumps(data), headers=headers)
    assert rv.status_code == 400


def test_payment_invalid_input(session, client, jwt, app):
    """Assert that the endpoint returns 201."""
    token = jwt.create_jwt(get_claims(), token_header)
    headers = {'Authorization': f'Bearer {token}', 'content-type': 'application/json'}
    data = {
        'payment_info': {
            'method_of_payment': 'CC'
        },
        'business_info': {
            'business_identifier': 'CP1234',
            'corp_type': 'PC',
            'business_name': 'ABC Corp',
            'contact_info': {
                'city': 'Victoria',
                'postal_code': 'V8P2P2',
                'province': 'BC',
                'address_line_1': '100 Douglas Street',
                'country': 'CA'
            }
        }, 'filing_info': {
            'filing_types': [
                {
                    'filing_type_code': 'OTADD',
                    'filing_description': 'TEST'
                },
                {
                    'filing_type_code': 'OTANN'
                }
            ]
        }
    }
    rv = client.post(f'/api/v1/payments', data=json.dumps(data), headers=headers)
    assert rv.status_code == 400


def test_payment_get(session, client, jwt, app):
    """Assert that the endpoint returns 201."""
    token = jwt.create_jwt(get_claims(), token_header)
    headers = {'Authorization': f'Bearer {token}', 'content-type': 'application/json'}
    data = {
        'payment_info': {
            'method_of_payment': 'CC'
        },
        'business_info': {
            'business_identifier': 'CP1234',
            'corp_type': 'CP',
            'business_name': 'ABC Corp',
            'contact_info': {
                'city': 'Victoria',
                'postal_code': 'V8P2P2',
                'province': 'BC',
                'address_line_1': '100 Douglas Street',
                'country': 'CA'
            }
        },
        'filing_info': {
            'filing_types': [
                {
                    'filing_type_code': 'OTADD',
                    'filing_description': 'TEST'
                },
                {
                    'filing_type_code': 'OTANN'
                }
            ]
        }
    }
    rv = client.post(f'/api/v1/payments', data=json.dumps(data), headers=headers)
    pay_id = rv.json.get('id')

    rv = client.get(f'/api/v1/payments/{pay_id}', headers=headers)
    assert rv.status_code == 200
    assert schema_utils.validate(rv.json, 'payment_response')[0]


def test_payment_get_exception(session, client, jwt, app):
    """Assert that the endpoint returns 201."""
    token = jwt.create_jwt(get_claims(), token_header)
    headers = {'Authorization': f'Bearer {token}', 'content-type': 'application/json'}
    pay_id = '123456sdf'

    rv = client.get(f'/api/v1/payments/{pay_id}', headers=headers)
    assert rv.status_code == 404

    pay_id = '9999999999'

    rv = client.get(f'/api/v1/payments/{pay_id}', headers=headers)
    assert rv.status_code == 400


def test_payment_put(session, client, jwt, app):
    """Assert that the endpoint returns 200."""
    token = jwt.create_jwt(get_claims(), token_header)
    headers = {'Authorization': f'Bearer {token}', 'content-type': 'application/json'}
    data = {
        'payment_info': {
            'method_of_payment': 'CC'
        },
        'business_info': {
            'business_identifier': 'CP1234',
            'corp_type': 'CP',
            'business_name': 'ABC Corp',
            'contact_info': {
                'city': 'Victoria',
                'postal_code': 'V8P2P2',
                'province': 'BC',
                'address_line_1': '100 Douglas Street',
                'country': 'CA'
            }
        },
        'filing_info': {
            'filing_types': [
                {
                    'filing_type_code': 'OTADD',
                    'filing_description': 'TEST'
                },
                {
                    'filing_type_code': 'OTANN'
                }
            ]
        }
    }
    rv = client.post(f'/api/v1/payments', data=json.dumps(data), headers=headers)
    pay_id = rv.json.get('id')

    transaction = factory_payment_transaction(pay_id)
    transaction.save()

    rv = client.put(f'/api/v1/payments/{pay_id}', data=json.dumps(data), headers=headers)
    assert rv.status_code == 200


def test_payment_put_incomplete_input(session, client, jwt, app):
    """Assert that the endpoint returns 201."""
    token = jwt.create_jwt(get_claims(), token_header)
    headers = {'Authorization': f'Bearer {token}', 'content-type': 'application/json'}
    data = {
        'payment_info': {
            'method_of_payment': 'CC'
        },
        'business_info': {
            'business_identifier': 'CP1234',
            'corp_type': 'CP',
            'business_name': 'ABC Corp',
            'contact_info': {
                'city': 'Victoria',
                'postal_code': 'V8P2P2',
                'province': 'BC',
                'address_line_1': '100 Douglas Street',
                'country': 'CA'
            }
        },
        'filing_info': {
            'filing_types': [
                {
                    'filing_type_code': 'OTADD',
                    'filing_description': 'TEST'
                },
                {
                    'filing_type_code': 'OTANN'
                }
            ]
        }
    }

    rv = client.post(f'/api/v1/payments', data=json.dumps(data), headers=headers)
    pay_id = rv.json.get('id')

    transaction = factory_payment_transaction(pay_id)
    transaction.save()

    data = {
        'payment_info': {
            'method_of_payment': 'CC'
        },
        'business_info': {
            'business_identifier': 'CP1234',
            'corp_type': 'CP',
            'business_name': 'ABC Corp',
            'contact_info': {
                'city': 'Victoria',
                'postal_code': 'V8P2P2',
                'province': 'BC',
                'address_line_1': '100 Douglas Street',
                'country': 'CA'
            }
        }
    }
    rv = client.put(f'/api/v1/payments/{pay_id}', data=json.dumps(data), headers=headers)
    assert rv.status_code == 400


def test_payment_put_invalid_input(session, client, jwt, app):
    """Assert that the endpoint returns 201."""
    token = jwt.create_jwt(get_claims(), token_header)
    headers = {'Authorization': f'Bearer {token}', 'content-type': 'application/json'}
    data = {
        'payment_info': {
            'method_of_payment': 'CC'
        },
        'business_info': {
            'business_identifier': 'CP1234',
            'corp_type': 'CP',
            'business_name': 'ABC Corp',
            'contact_info': {
                'city': 'Victoria',
                'postal_code': 'V8P2P2',
                'province': 'BC',
                'address_line_1': '100 Douglas Street',
                'country': 'CA'
            }
        },
        'filing_info': {
            'filing_types': [
                {
                    'filing_type_code': 'OTADD',
                    'filing_description': 'TEST'
                },
                {
                    'filing_type_code': 'OTANN'
                }
            ]
        }
    }

    rv = client.post(f'/api/v1/payments', data=json.dumps(data), headers=headers)
    pay_id = rv.json.get('id')

    transaction = factory_payment_transaction(pay_id)
    transaction.save()

    data = {
        'payment_info': {
            'method_of_payment': 'CC'
        },
        'business_info': {
            'business_identifier': 'CP1234',
            'corp_type': 'PC',
            'business_name': 'ABC Corp',
            'contact_info': {
                'city': 'Victoria',
                'postal_code': 'V8P2P2',
                'province': 'BC',
                'address_line_1': '100 Douglas Street',
                'country': 'CA'
            }
        }, 'filing_info': {
            'filing_types': [
                {
                    'filing_type_code': 'OTADD',
                    'filing_description': 'TEST'
                },
                {
                    'filing_type_code': 'OTANN'
                }
            ]
        }
    }
    rv = client.put(f'/api/v1/payments/{pay_id}', data=json.dumps(data), headers=headers)
    assert rv.status_code == 400
