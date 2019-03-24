from os import listdir
from datetime import date, timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from ckeditor.fields import RichTextField

from . import idoklad, widgets

class PriceCategory(models.Model):
    name = models.CharField('název', max_length=20)
    default_price = models.DecimalField('výchozí cena', max_digits=6, decimal_places=2)

    class Meta:
        verbose_name = 'cenová ketegorie'
        verbose_name_plural = 'cenové kategorie'

    def __str__(self):
        return self.name


class Product(models.Model):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.__class__.__name__ != 'Product':
            self._meta.get_field('img').choices = [(name, name) for name in listdir(
                settings.STATIC_ROOT + '/ffpasta/img/' + self.__class__.__name__.lower())]
    name = models.CharField('název', max_length=30, unique=True)
    description = RichTextField('popis', blank=True, null=True)
    img = models.CharField('obrázek', max_length=50)
    img_url = models.CharField(max_length=100, null=True, editable=False)
    published = models.BooleanField('publikováno', default=True)
    active = models.BooleanField('v nabídce', default=True)
    slug = models.SlugField(editable=False)
    price_category = models.ForeignKey('PriceCategory', verbose_name='cenová kategorie', on_delete=models.PROTECT)
    og_title = models.CharField('og titulek', max_length=80, null=True, blank=True)
    og_description = models.CharField('og popis', max_length=150, null=True, blank=True)

    class Meta:
        ordering = ['pasta__lengtḥ', 'name']

    def __str__(self):
        return self.name.capitalize()

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        self.img_url = self.get_img_url()
        return super().save(*args, **kwargs)

    def get_img_url(self):
        return '{}ffpasta/img/{}/{}'.format(settings.STATIC_URL, self.__class__.__name__.lower(), self.img)

    def get_unit(self):
        if hasattr(self, 'pasta'):
            return self.pasta.UNIT
        if hasattr(self, 'sauce'):
            return self.sauce.UNIT
        return ""

    def one_line_description(self):
        return self.description.replace('\n', '').replace('\r', '')

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
        ordering = ['name']

    def __str__(self):
        return self.name


class Delivery(models.Model):
    name = models.CharField('název', max_length=50)
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


class Price(models.Model):
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE, verbose_name='zákazník')
    price_category = models.ForeignKey('PriceCategory', on_delete=models.CASCADE, verbose_name='cenová kategorie')
    price = models.DecimalField('jednotková cena', max_digits=6, decimal_places=2, blank=True)

    class Meta:
        verbose_name = 'cena'
        verbose_name_plural = 'ceny'

    def __str__(self):
        return '{} {}'.format(self.price_category, self.price)


class Customer(models.Model):
    name = models.CharField('jméno', max_length=50)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='customer',
                                verbose_name='uživatel', on_delete=models.PROTECT, unique=True, blank=True)
    id_idoklad = models.PositiveSmallIntegerField('id iDoklad', null=True, editable=False)
    ico = models.DecimalField('ičo', max_digits=8, decimal_places=0, null=True, blank=True)
    delivery = models.ForeignKey('Delivery', on_delete=models.PROTECT, verbose_name='Závoz')
    price_list = models.ManyToManyField('PriceCategory', through='Price')

    class Meta:
        verbose_name = 'zákazník'
        verbose_name_plural = 'zákazníci'

    def __str__(self):
        return self.name

    def get_dates(self):
        days = self.delivery.get_days()
        dates = []
        minimal = 1 if timezone.now().hour < 12 else 2
        start_day = date.today() + timedelta(days=minimal)
        for d in range(60):
            new_date = start_day + timedelta(days=d)
            if new_date.weekday() in days:
                dates.append(new_date.__str__())
        return dates

    def get_ico(self):
        return f'{int(self.ico):08d}' if self.ico else ''


class Order(models.Model):
    REJECTED = 0
    PENDING = 1
    ACCEPTED = 2
    FINISHED = 3
    STATUS_CHOICES = (
        (REJECTED, 'zamítnuto'),
        (PENDING, 'čeká na přijetí'),
        (ACCEPTED, 'přijato'),
        (FINISHED, 'hotovo'),
    )
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name='zákazník')
    datetime_ordered = models.DateTimeField('objednáno', null=True)
    date_required = models.DateField('datum dodání')
    status = models.SmallIntegerField('stav', default=1, choices=STATUS_CHOICES)
    my_note = models.CharField('moje poznámka', max_length=100, null=True, blank=True)
    customer_note = models.CharField('poznámka zákazníka', max_length=100, null=True, blank=True)
    invoiced = models.BooleanField('fakturováno', default=False, editable=False)

    class Meta:
        verbose_name = 'objednávka'
        verbose_name_plural = 'objednávky'

    def __str__(self):
        return '{}: {}'.format(self.id, self.items_to_str())

    def get_items(self):
        return self.item_set.all()

    def items_to_str(self):
        return ', '.join(['{} {}{}'.format(item.name, item.quantity, item.item.get_unit()) for item in self.get_items()])

    def items_for_idoklad(self):
        return [{
            'Amount': item.quantity,
            'Name': item.name,
            'Unit': item.item.get_unit(),
            'UnitPrice': float(item.unit_price) } for item in self.get_items()]

    def invoice(self):
        response = idoklad.post_invoice(order=self)
        if response.status_code == 200:
            self.invoiced = True
            self.save(update_fields=['invoiced'])
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


class Item(models.Model):
    order = models.ForeignKey('Order', on_delete=models.PROTECT)
    item = models.ForeignKey('Product', on_delete=models.PROTECT, verbose_name='produkt')
    quantity = models.SmallIntegerField('množství')
    name = models.CharField('produkt', max_length=30, editable=False)
    unit_price = models.DecimalField('jednotková cena', max_digits=6, decimal_places=2, blank=True)

    class Meta:
        verbose_name = 'položka'
        verbose_name_plural = 'položky'

    def __str__(self):
        return '{} {}{}'.format(self.name, self.quantity, self.item.get_unit())

    def save(self, *args, **kwargs):
        self.name = self.item.name
        if not self.unit_price:
            user_price = Price.objects.filter(customer=self.order.customer, price_category=self.item.price_category).first()
            if user_price:
                self.unit_price = user_price.price
            else:
                self.unit_price = self.item.price_category.default_price
        return super().save(*args, **kwargs)

    def get_price(self):
        return self.quantity * self.unit_price


class Section(models.Model):
    headline = models.CharField('nadpis', max_length=50)
    link = models.CharField('odkaz v menu', max_length=25)
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
