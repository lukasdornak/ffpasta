import json
from os import listdir
from datetime import date, datetime, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import models, transaction
from django.forms.models import model_to_dict
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.text import slugify
from ckeditor.fields import RichTextField


from . import idoklad, widgets


class PriceCategory(models.Model):
    name = models.CharField('název', max_length=20, unique=True)
    unit_price = models.DecimalField('jednotková cena', max_digits=6, decimal_places=2)

    class Meta:
        verbose_name = 'cenová ketegorie'
        verbose_name_plural = 'cenové kategorie'

    def __str__(self):
        return self.name


class Product(models.Model):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._meta.get_field('img').choices = [(name, name) for name in listdir(settings.STATIC_ROOT + '/ffpasta/img/product')]
    name = models.CharField('název', max_length=30, unique=True)
    description = RichTextField('popis', blank=True, null=True)
    img = models.CharField('obrázek', max_length=50)
    published = models.BooleanField('publikováno', default=True)
    active = models.BooleanField('v nabídce', default=True)
    slug = models.SlugField(editable=False)
    price_category = models.ForeignKey('PriceCategory', verbose_name='cenová kategorie', on_delete=models.PROTECT, null=True, blank=True)
    unit_price = models.DecimalField('jednotková cena', max_digits=6, decimal_places=2, null=True, blank=True)
    og_title = models.CharField('titulek pro sdílení', max_length=80, null=True, blank=True)
    og_description = models.CharField('popis pro sdílení', max_length=150, null=True, blank=True)
    in_stock = models.PositiveSmallIntegerField('na skladě', default=0, editable=False)

    class Meta:
        ordering = ['pasta__lengtḥ', 'name']

    def __str__(self):
        return self.name.capitalize()

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        return super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.price_category and self.unit_price:
            raise ValidationError('Nelze nastavit zároveň jednotkovou cenu i cenovou kategorii.')
        if self.price_category is None and self.unit_price is None:
            raise ValidationError('Je třeba nastavit buď jednotkovou cenu a nebo cenovou kategorii.')

    def img_url(self):
        return '{}ffpasta/img/product/{}'.format(settings.STATIC_URL, self.img)

    def get_unit(self):
        if hasattr(self, 'pasta'):
            return self.pasta.UNIT
        if hasattr(self, 'sauce'):
            return self.sauce.UNIT
        return ""

    def one_line_description(self):
        return self.description.replace('\n', '').replace('\r', '')

    def get_og_title(self):
        return self.og_title or self.name

    def get_og_description(self):
        return self.og_description or self.one_line_description()

    def get_og_img_url(self):
        return self.img_url().replace('.png', '_black.png')

    def assign_to_price_category(self, price_category):
        if self.price_category == price_category:
            return False
        self.price_category = price_category
        self.unit_price = None
        self.save(update_fields=['price_category', 'unit_price'])
        return True

    def get_unit_price(self):
        return self.unit_price or self.price_category.unit_price

    get_unit_price.short_description = 'jednotková cena'


class StockTransaction(models.Model):
    PRODUCTION = 'p'
    COMPLETION = 'c'
    LIQUIDATION = 'l'
    TYPE_CHOICES = (
        (PRODUCTION, 'produkce'),
        (COMPLETION, 'kompletace'),
        (LIQUIDATION, 'likvidace'),
    )
    product = models.ForeignKey('Product', verbose_name='produkt', on_delete=models.CASCADE)
    quantity = models.PositiveSmallIntegerField('množství',)
    datetime = models.DateTimeField('datum a čas', auto_now_add=True)
    transaction_type = models.CharField('druh pohybu', max_length=1, choices=TYPE_CHOICES)
    committed_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='uživatel', on_delete=models.PROTECT,
                                     editable=False)
    note = models.CharField('poznámka', max_length=150, null=True, blank=True)
    order = models.ForeignKey('Order', verbose_name='objednávka', on_delete=models.SET_NULL, editable=False,
                              null=True, blank=True)

    class Meta:
        verbose_name = 'pohyb skladu'
        verbose_name_plural = 'pohyby skladu'
        ordering = ['-datetime']

    def save(self, *args, **kwargs):
        if self.id is None:
            with transaction.atomic():
                self._process()
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.transaction_type == 'c' and self.order is None:
            raise ValidationError('Je třeba zadat objednávku, která má být kompletována')

    def _process(self):
        self.product.in_stock += self.quantity if self.transaction_type == 'p' else - self.quantity
        self.product.in_stock = max(self.product.in_stock, 0)
        self.product.save()


class Pasta(Product):
    UNIT = 'kg'
    SHORT = 0
    LONG = 1
    LENGTH_CHOICES = (
        (SHORT, 'krátké'),
        (LONG, 'dlouhé'),
    )
    length = models.PositiveSmallIntegerField('délka', choices=LENGTH_CHOICES)

    class Meta:
        verbose_name = 'těstovina'
        verbose_name_plural = 'těstoviny'
        ordering = ['length', 'name']


class Sauce(Product):
    UNIT = 'ks'
    MUSTARD = 0
    PESTO = 1
    TYPE_CHOICES = (
        (MUSTARD, 'hořčice'),
        (PESTO, 'pesto'),
    )
    sauce_type = models.PositiveSmallIntegerField('hořčice/pesto', choices=TYPE_CHOICES)

    class Meta:
        verbose_name = 'hořčice/pesto'
        verbose_name_plural = 'hořčice a pesta'
        ordering = ['-sauce_type', 'name']

    def __str__(self):
        return self.name


class Delivery(models.Model):
    name = models.CharField('název', max_length=50, unique=True)
    description = models.TextField('popis', null=True, blank=True)
    monday = models.BooleanField('pondělí', default=False)
    tuesday = models.BooleanField('úterý', default=False)
    wednesday = models.BooleanField('středa', default=False)
    thursday = models.BooleanField('čtvrtek', default=False)
    friday = models.BooleanField('pátek', default=False)
    saturday = models.BooleanField('soboa', default=False)
    sunday = models.BooleanField('neděle', default=False)

    class Meta:
        verbose_name = 'závoz'
        verbose_name_plural = 'závozy'

    def __str__(self):
        return self.name

    def get_days(self):
        fields = [self.monday, self.tuesday, self.wednesday, self.thursday, self.friday, self.saturday, self.sunday]
        days = []
        for index, field in enumerate(fields):
            if field:
                days.append(index)
        return days

    @classmethod
    def get_default_days(self):
        field_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        days = []
        for index, field_name in enumerate(field_names):
            if Delivery.objects.filter(**{field_name: True}).exists():
                days.append(index)
        return days


class Price(models.Model):
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE, verbose_name='zákazník')
    price_category = models.ForeignKey('PriceCategory', on_delete=models.CASCADE, verbose_name='cenová kategorie', null=True, blank=True)
    product = models.ForeignKey('Product', on_delete=models.CASCADE, verbose_name='produkt', null=True, blank=True)
    unit_price = models.DecimalField('jednotková cena', max_digits=6, decimal_places=2, blank=True)

    class Meta:
        verbose_name = 'cena'
        verbose_name_plural = 'ceny'
        unique_together = (('customer', 'price_category'), ('customer', 'product'))

    def __str__(self):
        return '{} {}'.format(self.price_category, self.unit_price)

    def clean(self):
        if self.price_category is None and self.product is None:
            raise ValidationError('Vyber cenovou kateorii, nebo kontrétní produkt, pro který chceš nastavit cenu.')


class Address(models.Model):
    street = models.CharField('ulice a čp', max_length=50)
    postal_code = models.DecimalField('PSČ', max_digits=5, decimal_places=0)
    city = models.CharField('město', max_length=50)
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE, verbose_name='Zákazník', related_name='delivery_addresses')
    delivery = models.ManyToManyField('Delivery', verbose_name='Závoz', blank=True)

    class Meta:
        verbose_name = 'dodací adresa'
        verbose_name_plural = 'dodací adresy'

    def __str__(self):
        return f'{ self.customer }: { self.street }, { self.city }'

    def get_dates(self):
        days = set()
        for delivery in self.delivery.all():
            days.update(delivery.get_days())

        if not len(days):
            days = Delivery.get_default_days()

        dates = []
        minimal = 1 if timezone.now().hour < 12 else 2
        start_day = date.today() + timedelta(days=minimal)
        for d in range(60):
            new_date = start_day + timedelta(days=d)
            if new_date.weekday() in days:
                dates.append(new_date.__str__())
        return dates


class Customer(models.Model):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_invoice_address = model_to_dict(self, fields=['name', 'street', 'postal_code', 'city'])

    name = models.CharField('firma', max_length=50)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='customer',
                                verbose_name='uživatel', on_delete=models.PROTECT, unique=True, blank=True)
    id_idoklad = models.PositiveSmallIntegerField('id iDoklad', null=True, editable=False)
    ico = models.DecimalField('ičo', max_digits=8, decimal_places=0, null=True, blank=True)
    street = models.CharField('ulice a čp', max_length=50, null=True, blank=True)
    postal_code = models.DecimalField('PSČ', max_digits=5, decimal_places=0, null=True, blank=True)
    city = models.CharField('město', max_length=50, null=True, blank=True)
    email_is_verified = models.BooleanField('potvrzená emailová adresa', default=False, editable=False)
    same_delivery_address = models.BooleanField('dodací adresa stejná jako fakturační', default=True)

    class Meta:
        verbose_name = 'zákazník'
        verbose_name_plural = 'zákazníci'

    def __str__(self):
        return self.name or self.user.email

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.has_invoice_address() and self.same_delivery_address:
            self.sync_delivery_address()
        if self.has_complete_profile() and self.ico and self.invoice_address_changed():
            idoklad.sync_customers_to_idoklad(Customer.objects.filter(id=self.id))

    def get_ico(self):
        return f'{int(self.ico):08d}' if self.ico else ''

    @classmethod
    def self_register(cls, email, ico, password):
        with transaction.atomic():
            user = User.objects.create_user(email=email, password=password)
            obj = Customer.objects.create(user=user, ico=ico)
            return obj

    def send_verification_code(self):
        token = get_random_string(length=32)
        cache.set(f'EMAIL_VERIFICATION_TOKEN_FOR_CUSTOMER_{ self.id }', token, 1800)
        msg = 'Dobrý den,\n\n'\
              'Děkujeme za Vaši registraci.\n'\
              'Pro její dokončení je potřeba potvrdit Vaši e-mailovou adresu na níže uvedeném odkazu.\n\n'\
              f'http://{ settings.DOMAIN }/overeni-emailu/{ self.id }/{ token }/\n\n'\
              f'Odkaz je platný do { (datetime.now() + timedelta(minutes=30)).strftime("%H:%M %d.%m. %Y") }.'
        self.user.email_user(subject='registrace ffpasta', message=msg)

    def verify_email(self):
        self.email_is_verified = True
        self.save(update_fields=['email_is_verified'])

    def has_invoice_address(self):
        return self.street and self.postal_code and self.city

    def has_complete_profile(self):
        return self.email_is_verified and self.has_invoice_address()

    def sync_delivery_address(self):
        same_address = self.delivery_addresses.filter(street=self.street,
                                                      postal_code=self.postal_code,
                                                      city=self.city).first()
        if same_address:
            self.delivery_addresses.exclude(id=same_address.id).delete()
        else:
            self.delivery_addresses.all().delete()
            Address.objects.create(street=self.street,
                                   postal_code=self.postal_code,
                                   city=self.city,
                                   customer=self)

    def invoice_address_changed(self):
        return self._original_invoice_address != model_to_dict(self, fields=['name', 'street', 'postal_code', 'city'])


class Order(models.Model):
    REJECTED = 0
    PENDING = 1
    CONFIRMED = 2
    COMPLETED = 3
    STATUS_CHOICES = (
        (REJECTED, 'zamítnuto'),
        (PENDING, 'čeká na potvrzení'),
        (CONFIRMED, 'potvrzeno'),
        (COMPLETED, 'hotovo'),
    )
    MANAGE_ERR_MSG = 'Objednávka č. {} nemohla být {}, protože je již ve stavu {}.'
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name='zákazník')
    datetime_ordered = models.DateTimeField('objednáno', null=True)
    date_required = models.DateField('datum dodání')
    status = models.SmallIntegerField('stav', default=1, choices=STATUS_CHOICES)
    my_note = models.CharField('moje poznámka', max_length=100, null=True, blank=True)
    customer_note = models.CharField('poznámka zákazníka', max_length=100, null=True, blank=True)
    invoiced = models.BooleanField('fakturováno', default=False, editable=False)
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, verbose_name='dodací adresa', null=True, blank=True)
    delivery_note_number = models.PositiveSmallIntegerField('č. dodacího listu', null=True, editable=False)
    delivery_note_recipient = models.CharField(max_length=150, null=True, editable=False)

    class Meta:
        verbose_name = 'objednávka'
        verbose_name_plural = 'objednávky'

    def __str__(self):
        return '{}: {}'.format(self.id, self.items_to_str())

    def get_items(self):
        return self.item_set.all()

    def items_to_str(self):
        return ', '.join(['{} {}{}'.format(item.name, item.quantity, item.product.get_unit()) for item in self.get_items()])

    def items_for_idoklad(self):
        return idoklad.ItemList([
            idoklad.Item({
            'Amount': item.quantity,
            'Name': item.name,
            'Unit': item.product.get_unit(),
            'UnitPrice': float(item.unit_price) }) for item in self.get_items()
        ])

    def invoice(self, **kwargs):
        response = idoklad.post_invoice(customer=self.customer, items=self.items_for_idoklad(), **kwargs)
        if response.status_code == 200:
            self.invoiced = True
            self.save(update_fields=['invoiced'])
            return 0
        return response

    @classmethod
    def delivery_notes_invoice_title(cls, queryset):
        if len(queryset) > 1:
            return  "Na základě dodacích listů:\n{}Vám fakturujeme tyto položky:".format(
                ''.join([f'č. { order.delivery_note_number } ze dne { order.date_required }\n' for order in queryset]) )
        order = queryset.first()
        return f'Na základě dodacího listu č. { order.delivery_note_number } ze dne { order.date_required } Vám fakturujeme tyto položky:'

    @classmethod
    def invoice_delivery_notes(cls, queryset):
        customer = queryset.first().customer if queryset.exists() else None
        if customer is not None:
            queryset.filter(customer=customer)  # prevent multiple customers in queryset
            item_list = idoklad.ItemList()
            for order in queryset.iterator():
                item_list += order.items_for_idoklad()
            response = idoklad.post_invoice(customer=customer, items=item_list,
                                            ItemsTextPrefix=cls.delivery_notes_invoice_title(queryset))
            if response.status_code == 200:
                queryset.update(invoiced=True)
                return 0
            return response

    def is_history(self):
        return self.date_required < date.today()

    def get_total_price(self):
        sum = 0
        for item in self.get_items():
            sum = sum + item.get_price()
        return sum

    def format_price(self):
        import locale
        locale.setlocale(locale.LC_ALL, '')
        return locale.format('%d', self.get_total_price(), True)

    get_total_price.short_description = 'celková cena'

    def missing_product(self):
        for item in self.get_items():
            if item.quantity > item.product.in_stock:
                return item.product
        return False

    def do_reject(self):
        if self.status == self.PENDING:
            self.status = self.REJECTED
            self.save(update_fields=['status'])
            return None
        return self.MANAGE_ERR_MSG.format(self.id, 'odmítnuta', self.get_status_display())

    def do_confirm(self):
        if self.status == self.PENDING:
            self.status = self.CONFIRMED
            self.save(update_fields=['status'])
            return None
        return self.MANAGE_ERR_MSG.format(self.id, 'potvrzena', self.get_status_display())

    def do_complete(self, user):
        if self.status == self.PENDING or self.status == self.CONFIRMED:
            missing = self.missing_product()
            if missing:
                return f'Objednávka č. { self.id } nemohla být dokončena, protože na skladě není dostatek produktu { missing }.'
            with transaction.atomic():
                self.status = self.COMPLETED
                self.save(update_fields=['status'])
                for item in self.get_items():
                    StockTransaction.objects.create(quantity=item.quantity, product=item.product, committed_by=user,
                                                    order=self, transaction_type='c')
            return None
        return self.MANAGE_ERR_MSG.format(self.id, 'zabalena', self.get_status_display())

    def create_delivery_note(self):
        if self.delivery_note_number is not None:
            return f'Objednávka č. { self.id } již má dodací list č. { self.delivery_note_number }'
        self.delivery_note_number = Order.next_delivery_note_number()
        self.delivery_note_recipient = json.dumps({
            'name': self.customer.name,
            'ico': str(self.customer.ico),
            'street': self.customer.street,
            'postal_code': str(self.customer.postal_code),
            'city': self.customer.city,
            'delivery_address': f'{ self.address.street }, { self.address.postal_code } { self.address.city }' if self.address else None
        })
        self.save(update_fields=['delivery_note_number', 'delivery_note_recipient'])
        return self.delivery_note_number

    def get_delivery_note_recipient(self):
        return json.loads(self.delivery_note_recipient if self.delivery_note_recipient else '{}')

    def send_manage_token_to_admins(self, token):
        message = f'Zákazník { self.customer } si objednal tyto produkty:\n\n{ self.items_to_str() }\n\n' \
                  f'a rád by je dostal: { self.date_required.strftime("%-d.%-m. %Y") }.\n\n' \
                  f'Pro potvrzení data dodání použij tento odkaz:\n\n' \
                  f'https://{ settings.DOMAIN }/potvrdit-objednavku/{ self.id }/{ token }/\n\n' \
                  f'Pro odmítnutí této objednávky použij tento odkaz:\n\n' \
                  f'https://{ settings.DOMAIN }/odmitnout-objednavku/{ self.id }/{ token }/\n\n' \
                  f's přáním pěknéh dne\nVáš objednávkový systém FFpasta.cz'
        admin_users = User.objects.filter(is_staff=True)
        for admin_user in admin_users.iterator():
            if admin_user.has_perm('ffpasta.can_change_order'):
                admin_user.email_user(subject='Nová objednávka', from_email='admin@ffpasta.cz', message=message)

    @classmethod
    def next_delivery_note_number(cls):
        last = cls.objects.order_by('delivery_note_number').last()
        return (last.delivery_note_number if last and last.delivery_note_number else 0) + 1


class Item(models.Model):
    order = models.ForeignKey('Order', on_delete=models.CASCADE)
    product = models.ForeignKey('Product', on_delete=models.PROTECT, verbose_name='produkt')
    quantity = models.SmallIntegerField('množství')
    name = models.CharField('produkt', max_length=30, editable=False)
    unit_price = models.DecimalField('jednotková cena', max_digits=6, decimal_places=2, blank=True)

    class Meta:
        verbose_name = 'položka'
        verbose_name_plural = 'položky'

    def __str__(self):
        return '{} {}{}'.format(self.name, self.quantity, self.product.get_unit())

    def save(self, *args, **kwargs):
        self.name = self.product.name
        if not self.unit_price:
            user_price = Price.objects.filter(models.Q(customer=self.order.customer),
                        models.Q(price_category=self.product.price_category) | models.Q(product=self.product)).first()
            if user_price:
                self.unit_price = user_price.unit_price
            else:
                self.unit_price = self.product.get_unit_price()
        return super().save(*args, **kwargs)

    def get_price(self):
        return self.quantity * self.unit_price


class Section(models.Model):
    headline = models.CharField('nadpis', max_length=50)
    link = models.CharField('odkaz v menu', max_length=25, unique=True)
    text = RichTextField('obsah', blank=True, null=True, default=None)
    slug = models.SlugField(editable=False, unique=True)
    widget = models.CharField(max_length=1, choices=widgets.Widget.get_choices(),
                              null=True, editable=False)

    class Meta:
        verbose_name = 'text'
        verbose_name_plural = 'texty'
        ordering = ['id']

    def save(self, *args, **kwargs):
        self.slug = slugify(self.headline)
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.headline

    def get_widget(self):
        return widgets.Widget.get_class(self.widget)


class Recipe(models.Model):
    name = models.CharField('název', max_length=150)
    text = RichTextField('postup')
    product = models.ForeignKey('Product', on_delete=models.CASCADE, verbose_name='produkt')
    published = models.BooleanField('publikováno')

    class Meta:
        verbose_name = 'recept'
        verbose_name_plural = 'recepty'

    def __str__(self):
        return self.name


class Difference(models.Model):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._meta.get_field('img').choices = [(name, name) for name in listdir(
            settings.BASE_DIR + '/ffpasta/static/ffpasta/img/difference')]
    header = models.CharField('nadpis', max_length=50)
    img = models.CharField('obrázek', max_length=50)
    ffpasta = models.CharField('ffpasta', max_length=200)
    others = models.CharField('ostatní', max_length=200)
    published = models.BooleanField('publikováno')

    class Meta:
        verbose_name = 'rozdíl'
        verbose_name_plural = 'rozdíly'
        ordering = ['id']

    def __str__(self):
        return self.header

    def img_url(self):
        return '{}ffpasta/img/difference/{}'.format(settings.STATIC_URL, self.img)
