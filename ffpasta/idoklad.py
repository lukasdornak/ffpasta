import json, requests
from django.conf import settings
from django.core.cache import cache


class Item(dict):
    def _is_addable(self, other):
        return self['Name'] == other['Name'] and \
               self['Unit'] == other['Unit'] and \
               self['UnitPrice'] == other['UnitPrice']

    def _try_addable(self, other):
        if not self._is_addable(other):
            raise TypeError(f"Diferent items {{Name:{ self['Name'] }, Unit:{ self['Unit']}, UnitPrice:{ self['UnitPrice'] }}} "\
                            f"and {{Name:{ other['Name'] }, Unit:{ other['Unit']}, UnitPrice:{ other['UnitPrice'] }}}")

    def __add__(self, other):
        self._try_addable(other)
        result = self.copy()
        result['Amount'] += other['Amount']
        return result

    def __iadd__(self, other):
        self._try_addable(other)
        self['Amount'] += other['Amount']
        return self


class ItemList(list):
    def append(self, new_item: Item):
        for item in self:
            if item._is_addable(new_item):
                item += new_item
                return None
        super().append(new_item)

    def __add__(self, other):
        result = self.copy()
        result += other
        return result

    def __iadd__(self, other):
        for new_item in other:
            self.append(new_item)
        return self


def _get_access_token():
    """
    Retrieve and return a new access token from iDoklad
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
    """
    Return an access token.

    Get the access token from cache or obtain a new token from iDoklad
    and store it in cache for next use
    """
    access_token = cache.get('idoklad_access_token', None)
    if access_token is None:
        cache.set('idoklad_access_token', _get_access_token(), None)
        access_token = cache.get('idoklad_access_token', '')
    return str(access_token)


def access_decorator(original_function):
    """
    Provide authorization interface for functions requesting iDoklad api.

    Add authorization header with access token to use in request.
    when request fails with 401-unauthorized, renew access token and repeat the request.
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
def post_invoice(headers, customer, items, **kwargs):
    """
    Post new invoice to iDoklad.

    Get a default invoice dictionary, update it with data and send it back.
    """
    invoice = get_default_invoice()
    invoice['PurchaserId'] = customer.id_idoklad
    default_item = invoice['IssuedInvoiceItems'].pop(0)
    for item in items:
        new_item = default_item.copy()
        new_item.update(item)
        new_item.update(kwargs)
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


def sync_customers_from_idoklad(customers):
    """
    Synchronize local Customers with remote contacts in iDoklad.

    Get all contacts from iDoklad, then iterate through given Customer queryset
    if contact with the same ico found, update Customer with contact's data.
    """
    contacts = get_contacts()
    for customer in customers.iterator():
        ico = customer.get_ico()
        for contact in contacts:
            if contact['IdentificationNumber'] == ico:
                customer.id_idoklad = contact['Id']
                customer.name = contact['CompanyName']
                if contact['Street']:
                    customer.street = contact['Street']
                if contact['PostalCode']:
                    customer.postal_code = int(contact['PostalCode'])
                if contact['City']:
                    customer.city = contact['City']
                customer.save()


@access_decorator
def _get_contact_by_id(headers, id):
    url = settings.IDOKLAD_API_URL + '/api/v2/Contacts/' + str(id)
    return requests.get(url=url, headers=headers)


def get_contact_by_id(id):
    _default_contact = _get_default_contact(id)
    return json.loads(_default_contact.text)


@access_decorator
def put_contact(headers, contact, **kwargs):
    """
    Update contact in iDoklad.

    Get current contact from iDoklad by id, update it, and send back to iDoklad
    """
    remote_contact = get_contact_by_id(id=contact['Id'])
    remote_contact.update(contact)
    url = settings.IDOKLAD_API_URL + '/api/v2/Contacts/' + contact['Id']
    headers.update({'Content-Type': 'application/json'})
    return requests.put(url=url, data=json.dumps(remote_contact), headers=headers)


def sync_customers_to_idoklad(customers):
    """
    Synchronize remote contacts in iDoklad with local Customers data.

    Get all contacts from iDoklad, then iterate through given Customer queryset
    if contact with the same ico found, update it with Customer's data.
    If contact has changed, put it to iDoklad.
    If no corresponding contact found, Post new one to iDoklad.
    """
    contacts = get_contacts()
    for customer in customers:
        ico = customer.get_ico()
        contact_found = False
        for contact in contacts:
            if contact['IdentificationNumber'] == ico:
                customer.id_idoklad = contact['Id']
                contact_changed = False
                if customer.name != contact['CompanyName']:
                    contact['CompanyName'] = customer.name
                    contact_changed = True
                if customer.street and customer.street != contact['Street']:
                    contact['Street'] = customer.street
                    contact_changed = True
                if customer.postal_code and str(customer.postal_code) != contact['PostalCode']:
                    contact['PostalCode'] = str(customer.postal_code)
                    contact_changed = True
                if customer.city and customer.city != contact['City']:
                    contact['City'] = customer.city
                    contact_changed = True
                customer.save(update_fields=['id_doklad'])
                if contact_changed:
                    put_contact(contact)
                contact_found = True
        if not contact_found:
            response = post_contact(customer=customer)
            if response.status_code == 200:
                customer.id_idoklad = json.loads(response.text)['Id']
                customer.save(update_fields=['id_idoklad'])



@access_decorator
def _get_default_contact(headers):
    url = settings.IDOKLAD_API_URL + '/api/v2/Contacts/Default'
    return requests.get(url=url, headers=headers)


def get_default_contact():
    _default_contact = _get_default_contact()
    return json.loads(_default_contact.text)


@access_decorator
def post_contact(headers, customer, **kwargs):
    """
    Post new contact to iDoklad.

    Retrieve a default contact dictionary, update it with customer data and post it.
    Save customer with new id_doklad if success.
    """
    contact = get_default_contact()
    contact.update({
        'CompanyName': customer.name,
        'IdentificationNumber': str(customer.ico),
        'Email': customer.user.email,
        'Street': customer.street,
        'PostalCode': str(customer.postal_code),
        'City': customer.city
    })
    url = settings.IDOKLAD_API_URL + '/api/v2/Contacts'
    headers.update({'Content-Type': 'application/json'})
    return requests.post(url=url, data=json.dumps(contact), headers=headers)
