import json, requests
from django.conf import settings
from django.core.cache import cache


def _get_access_token():
    """retrieve and return a new access token from iDoklad api
    """
    url = settings.IDOKLAD_AUTH_URL
    data = {
        'scope': 'idoklad_api',
        'client_id': settings.IDOKLAD_CLIENT_ID,
        'client_secret': settings.IDOKLAD_CLIENT_SECRET,
        'grant_type': 'client_credentials'}
    response = requests.post(url=url, data=data)
    return json.loads(response.text).get('access_token', None)


def get_access_token():
    """retrieve the access token from cache or
    obtain and store a new token from iDoklad api
    """
    access_token = cache.get('idoklad_access_token', None)
    if access_token is None:
        cache.set('idoklad_access_token', _get_access_token(), None)
        access_token = cache.get('idoklad_access_token')
    return access_token


def access_decorator(original_function):
    """add authorization header with access token to use in request
    when request fail with 401-unauthorized, renew access token and repeat the request
    """
    def wrapper_function(*args, **kwargs):
        access_token = get_access_token()
        headers = {'Authorization': 'Bearer ' + access_token}
        response = original_function(headers=headers, *args, **kwargs)
        if response.status_code == 401:
            cache.delete('idoklad_access_token')
            access_token = get_access_token()
            headers = {'Authorization': 'Bearer ' + access_token}
            response = original_function(headers=headers, *args, **kwargs)
        return response
    return wrapper_function


@access_decorator
def _get_default_invoice(headers):
    url = settings.IDOKLAD_API_URL + '/api/v2/IssuedInvoices/Default'
    return requests.get(url=url, headers=headers)


def get_default_invoice():
    _default_invoice = _get_default_invoice()
    return json.loads(_default_invoice.text)


@access_decorator
def post_invoice(headers, order):
    """retrieve a default invoice dictionary, update it with order data and post it
    """
    invoice = get_default_invoice()
    invoice['PurchaserId'] = order.customer.id_idoklad
    default_item = invoice['IssuedInvoiceItems'].pop(0)
    items = order.items_for_idoklad()
    for item in items:
        new_item = default_item.copy()
        new_item.update(item)
        invoice['IssuedInvoiceItems'].append(new_item)
    url = settings.IDOKLAD_API_URL + '/api/v2/IssuedInvoices'
    headers.update({'Content-Type': 'application/json'})
    return requests.post(url=url, data=json.dumps(invoice), headers=headers)


@access_decorator
def _get_contacts(headers):
    url = settings.IDOKLAD_API_URL + '/api/v2/Contacts'
    return requests.get(url=url, headers=headers)


def get_contacts():
    _contacts = _get_contacts()
    return json.loads(_contacts.text)['Data']


def connect_customers(customers):
    """get a list of iDoklad contacts, than iterate through given set of customers
    and look for its ico in contact list. if found, save customer with appropriate id_doklad
    """
    contacts = get_contacts()
    for customer in customers.iterator():
        ico = customer.get_ico()
        for contact in contacts:
            if contact['IdentificationNumber'] == ico:
                customer.id_idoklad = contact['Id']
                customer.save(update_fields=['id_idoklad'])
