import datetime
import weasyprint

from django.contrib.admin import AdminSite
from django.contrib import admin, messages
from django.db.models import Sum
from django.http import HttpResponse, HttpResponseRedirect
from django.forms import ValidationError
from django.shortcuts import redirect
from django.template.loader import get_template
from django.utils.formats import date_format
from django.utils.translation import gettext_lazy as _
from django.utils.safestring import mark_safe

from . import forms, models, idoklad


class ProductionAdminSite(AdminSite):
    site_header = "FFpasta - výroba"
    site_title = "Vyroba"
    index_title = "Vyroba"

    def has_permission(self, request):
        return request.user.is_active and request.user.is_worker


production_admin = ProductionAdminSite(name='production_admin')


def make_assign_to_price_category(price_category):
    def assign_to_price_category(modeladmin, request, queryset):
        for product in queryset:
            changed = product.assign_to_price_category(price_category)
            if changed:
                messages.info(request, f'Produkt { product.name } zařazen do cenové kategorie { price_category.name }')

    assign_to_price_category.short_description = f'Zařadit do cenové kategorie { price_category.name }'
    assign_to_price_category.__name__ = f'assign_to_price_category_{ price_category.pk }'

    return assign_to_price_category


class PublishMixin:
    actions = ['publish', 'hide']

    def publish(self, request, queryset):
        queryset.update(published=True)

    def hide(self, request, queryset):
        queryset.update(published=False)

    publish.short_description = 'Publikovat'
    hide.short_description = 'Skrýt'


class ProductMixin:
    actions = ['activate', 'deactivate']

    def activate(self, request, queryset):
        queryset.update(active=True)

    def deactivate(self, request, queryset):
        queryset.update(active=False)

    activate.short_description = 'Zařadit do nabídky'
    deactivate.short_description = 'Vyřadit z nabídky'

    def get_actions(self, request):
        actions = super().get_actions(request)

        for price_category in list(models.PriceCategory.objects.all()):
            action = make_assign_to_price_category(price_category)
            actions[action.__name__] = (action, action.__name__, action.short_description)
        return actions


@admin.register(models.PriceCategory)
class PriceCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'unit_price']


@admin.register(models.Pasta)
class PastaAdmin(ProductMixin, PublishMixin, admin.ModelAdmin):
    list_display = ['name', 'length', 'price_category', 'get_unit_price', 'published', 'active', 'in_stock']
    list_filter = ['length', 'price_category']


@admin.register(models.Sauce)
class SauceAdmin(ProductMixin, PublishMixin, admin.ModelAdmin):
    list_display = ['name', 'sauce_type', 'price_category', 'get_unit_price', 'published', 'active', 'in_stock']
    list_filter = ['sauce_type']


@admin.register(models.Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'monday', 'tuesday', 'wednesday', 'thursday',
                    'friday', 'saturday', 'sunday']


@admin.register(models.Address)
class AddressAdmin(admin.ModelAdmin):
    filter_horizontal = ['delivery']


class PriceInline(admin.TabularInline):
    model = models.Price
    form = forms.PriceAdminForm
    extra = 0


class AddressInline(admin.TabularInline):
    model = models.Address
    filter_horizontal = ['delivery']
    extra = 0


class HasIcoFilter(admin.SimpleListFilter):
    title = 'Ičo'
    parameter_name = 'má ičo'

    def lookups(self, request, model_admin):
        return (
            ('Yes', 'Ano'),
            ('No', 'Ne'),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == 'Yes':
            return queryset.filter(ico__isnull=False)
        elif value == 'No':
            return queryset.filter(ico__isnull=True)
        return queryset


class HasIdIDokladFilter(admin.SimpleListFilter):
    title = 'Kontakt iDokladu'
    parameter_name = 'kontakt iDokladu'

    def lookups(self, request, model_admin):
        return (
            ('Yes', 'Ano'),
            ('No', 'Ne'),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == 'Yes':
            return queryset.filter(id_idoklad__isnull=False)
        elif value == 'No':
            return queryset.filter(id_idoklad__isnull=True)
        return queryset


@admin.register(models.Customer)
class CustomerAdmin(admin.ModelAdmin):
    form = forms.CustomerAdminForm
    list_display = ['__str__', 'ico', 'user', 'has_id_idoklad', 'has_delivery', 'email_is_verified']
    readonly_fields = ['email_is_verified']
    list_filter = [HasIcoFilter, HasIdIDokladFilter]
    actions = ['sync_customers_to_idoklad', 'sync_customers_from_idoklad']
    inlines = [AddressInline, PriceInline]
    fieldsets = (
        (None, {
            'fields': ('name', 'ico', 'user'),
        }),
        ('Fakturační adresa', {
            'fields': ('street', 'postal_code', 'city', 'same_delivery_address'),
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        return ['user', 'id_idoklad'] if obj else ['id_idoklad']

    def has_id_idoklad(self, obj):
        return bool(obj.id_idoklad)

    def has_delivery(self, obj):
        return obj.delivery_addresses.all().exists() and not obj.delivery_addresses.filter(delivery=None)

    def sync_customers_to_idoklad(self, request, queryset):
        idoklad.sync_customers_to_idoklad(customers=queryset)

    def sync_customers_from_idoklad(self, request, queryset):
        idoklad.sync_customers_from_idoklad(customers=queryset)

    sync_customers_to_idoklad.short_description = 'synchronizovat kontakty v iDokladu podle zákazníků'
    sync_customers_from_idoklad.short_description = 'synchronizovat zákazníky podle kontaktů v iDokladu'
    has_id_idoklad.short_description = 'kontakt iDokladu'
    has_id_idoklad.boolean = True
    has_delivery.short_description = 'závoz nastaven'
    has_delivery.boolean = True


class ItemInline(admin.TabularInline):
    model = models.Item
    form = forms.ItemAdminForm
    formset = forms.ItemAdminFormSet
    extra = 0


class FutureDateFieldFilter(admin.FieldListFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        self.field_generic = '%s__' % field_path
        self.date_params = {k: v for k, v in params.items() if k.startswith(self.field_generic)}

        today = datetime.date.today()

        self.lookup_kwarg_since = '%s__gte' % field_path
        self.lookup_kwarg_until = '%s__lt' % field_path
        self.links = (
            (_('Today'), {
                self.lookup_kwarg_since: str(today),
                self.lookup_kwarg_until: str(today + datetime.timedelta(days=1)),
            }),
            ('následujících 7 dní', {
                self.lookup_kwarg_since: str(today),
                self.lookup_kwarg_until: str(today + datetime.timedelta(days=8)),
            }),
            ('následujících 30 dní', {
                self.lookup_kwarg_since: str(today),
                self.lookup_kwarg_until: str(today + datetime.timedelta(days=31)),
            }),
            (_('Any date'), {}),
        )
        if field.null:
            self.lookup_kwarg_isnull = '%s__isnull' % field_path
            self.links += (
                (_('No date'), {self.field_generic + 'isnull': 'True'}),
                (_('Has date'), {self.field_generic + 'isnull': 'False'}),
            )
        super().__init__(field, request, params, model, model_admin, field_path)

    def expected_parameters(self):
        params = [self.lookup_kwarg_since, self.lookup_kwarg_until]
        if self.field.null:
            params.append(self.lookup_kwarg_isnull)
        return params

    def choices(self, changelist):
        for title, param_dict in self.links:
            yield {
                'selected': self.date_params == param_dict,
                'query_string': changelist.get_query_string(param_dict, [self.field_generic]),
                'display': title,
            }


def clean_status(self):
    data = self.cleaned_data.get('status')
    if self.instance.invoiced and data < models.Order.CONFIRMED:
        raise ValidationError('Vyfakturovanou objednávku nelze vrátit.')
    return data


@admin.register(models.Order)
class OrderAdmin(admin.ModelAdmin):
    date_hierarchy = 'date_required'
    list_display = ['__str__', 'customer_note', 'customer', 'short_datetime', 'short_date',
                    'invoiced', 'delivery_note_number', 'status', 'my_note']
    list_filter = (
        ('date_required', admin.DateFieldListFilter),
        ('date_required', FutureDateFieldFilter),
        'status')
    readonly_fields = ['datetime_ordered', 'invoiced']
    list_editable = ['my_note']
    change_form_template = 'ffpasta/admin/order_change_form.html'
    inlines = [ItemInline]
    actions = ['reject', 'confirm', 'complete', 'create_delivery_note', 'download_delivery_note',
               'invoice_by_order', 'invoice_by_delivery_notes']
    search_fields = ['customer__name', 'customer__id']

    def short_datetime(self, obj):
        return obj.datetime_ordered.strftime("%d.%m. %H:%M")

    def short_date(self, obj):
        return obj.date_required.strftime("%d %m.")

    short_datetime.admin_order_field = 'datetime_ordered'
    short_datetime.short_description = 'Objednáno'
    short_date.admin_order_field = 'date_required'
    short_date.short_description = 'Datum dodání'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.filter(datetime_ordered__isnull=False).order_by('date_required')

    def changelist_view(self, request, extra_context=None):
        if not request.META.get('QUERY_STRING') and (
                request.META.get('HTTP_REFERER') is None or
                request.META.get('HTTP_REFERER').split('?')[0] != request.build_absolute_uri('?')):
            return HttpResponseRedirect('?date_required__gte={}&date_required__lt={}'.format(datetime.date.today(), datetime.date.today() + datetime.timedelta(days=8)))
        return super().changelist_view(request, extra_context)

    def response_change(self, request, obj):
        if "invoice" in request.POST:
            obj.save()
            invoice = obj.invoice()
            if invoice == 0:
                self.message_user(request, "Vyfakturováno")
            else:
                self.message_user(request, "Nepodařilo se vyfakturovat")
                # TO DO: log invoice fail !!!
            return HttpResponseRedirect(".")
        return super().response_change(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.invoiced:
            return False
        return super().has_delete_permission(request, obj)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj and obj.invoiced:
            return readonly_fields + ['customer']
        return readonly_fields

    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj, change, **kwargs)
        form.clean_status = clean_status
        return form

    def get_changelist_form(self, request, **kwargs):
        form = super().get_changelist_form(request, **kwargs)
        form.clean_status = clean_status
        return form

    def save_model(self, request, obj, form, change):
        if not change:
            obj.datetime_ordered = datetime.datetime.now()
        return super().save_model(request, obj, form, change)

    def reject(self, request, queryset):
        for order in queryset:
            err_msg = order.do_reject()
            if err_msg:
                messages.error(request, err_msg)
            else:
                messages.info(request, f'Objednávka č. { order.id } byla odmítnuta')

    def confirm(self, request, queryset):
        for order in queryset:
            err_msg = order.do_confirm()
            if err_msg:
                messages.error(request, err_msg)
            else:
                messages.info(request, f'Objednávka č. { order.id } byla potvrzena')

    def complete(self, request, queryset):
        for order in queryset:
            err_msg = order.do_complete(user=request.user)
            if err_msg:
                messages.error(request, err_msg)
            else:
                messages.info(request, f'Objednávka č. { order.id } byla dokončena')

    def create_delivery_note(self, request, queryset):
        for order in queryset:
            delivery_note_number = order.create_delivery_note()
            if isinstance(delivery_note_number, int):
                messages.success(request, f'Pro objednávku č. { order.id } byl vytvořen dodací list č. { delivery_note_number }')
            else:
                messages.warning(request, delivery_note_number)

    def download_delivery_note(self, request, queryset):
        queryset = queryset.filter(delivery_note_number__isnull=False)
        if queryset.exists():
            delivery_note_html = get_template('ffpasta/delivery_notes.html').render(context={'object_list': queryset})
            pdf_file = weasyprint.HTML(string=delivery_note_html).write_pdf()
            response = HttpResponse(pdf_file, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="dodaci_listy.pdf"'
            return response

    def invoice_by_order(self, request, queryset):
        for order in queryset.filter(invoiced=True):
            messages.info(request, f'Objednávka č. { order.id } již byla dříve vyfakturována.')
        for order in queryset.filter(invoiced=False):
            if order.invoice() == 0:
                messages.success(request, f'Objednávka č. { order.id } byla vyfakturována.')
            else:
                messages.error(request, f'Objednávku č. { order.id } se nepodařilo vyfakturovat.')

    def invoice_by_delivery_notes(self, request, queryset):
        queryset = queryset.filter(invoiced=False, delivery_note_number__isnull=False)
        if not queryset.exists():
            messages.warning(request, f'Žádné nevyfakturované dodací listy nebyly vybrány')
            return None
        if queryset.exclude(customer=queryset.first().customer).exists():
            messages.warning(request, f'Vybrané dodací listy jsou pro různé zákazníky')
            return None
        response = models.Order.invoice_delivery_notes(queryset)
        if response:
            messages.error(request, f'Dodací listy se nepodařilo vyfakturovat')
        else:
            messages.info(request, f'Dodací listy byly úspěšně vyfakturovány')

    reject.short_description = 'odmítnout'
    confirm.short_description = 'potvrdit'
    complete.short_description = 'dokončit'
    create_delivery_note.short_description = 'vytvořit dodací listy'
    download_delivery_note.short_description = 'stáhnout dodací listy'
    invoice_by_order.short_description = 'fakturovat jednotlivé obědnávky'
    invoice_by_delivery_notes.short_description = 'fakturovat dodací listy'


class TodayDeliveryOrder(models.Order):
    class Meta:
        proxy = True
        verbose_name = 'zásilka'
        verbose_name_plural = 'dnešní rozvoz'

    def customer_address(self):
        return self.address

    customer_address.short_description = 'adresa'


class UncommittedOrder(models.Order):
    class Meta:
        proxy = True
        verbose_name = 'neobjednaná objednávka'
        verbose_name_plural = 'neobjednané objednávky'


@admin.register(TodayDeliveryOrder)
class TodayDeliveryOrderAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'customer', 'customer_address', 'customer_note', 'my_note', 'get_total_price']
    list_filter = []

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.filter(datetime_ordered__isnull=False,
                               date_required=datetime.date.today(),
                               status__gte=models.Order.CONFIRMED)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ProductionTodayDeliveryOrderAdmin(TodayDeliveryOrderAdmin):

    def has_view_permission(self, request, obj=None):
        return True

    def has_module_permission(self, request):
        return True


@admin.register(UncommittedOrder)
class UncommittedOrderAdmin(admin.ModelAdmin):
    date_hierarchy = 'date_required'
    list_display = ['__str__', 'customer', 'date_required']
    list_filter = (('date_required', FutureDateFieldFilter),)
    readonly_fields = ['datetime_ordered']

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.filter(datetime_ordered__isnull=True)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(models.Section)
class SectionAdmin(admin.ModelAdmin):

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(models.Recipe)
class RecipeAdmin(PublishMixin, admin.ModelAdmin):
    list_display = ['__str__', 'product', 'published']


@admin.register(models.Difference)
class DifferenceAdmin(PublishMixin, admin.ModelAdmin):
    list_display = ['__str__', 'ffpasta', 'others', 'published']


class OrderedProduct(models.Product):
    class Meta:
        proxy = True
        verbose_name = 'Objednaný produkt'
        verbose_name_plural = 'Objednané produkty'


class ProductionFutureDateFieldFilter(admin.FieldListFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        self.field_generic = '%s__' % field_path
        self.date_params = {k: v for k, v in params.items() if k.startswith(self.field_generic)}

        today = datetime.date.today()

        self.lookup_kwarg_since = '%s__gte' % field_path
        self.lookup_kwarg_until = '%s__lt' % field_path
        self.links = (
            ('Dnes', {
                self.lookup_kwarg_since: str(today),
                self.lookup_kwarg_until: str(today + datetime.timedelta(days=1)),
            }),
            ('zítra', {
                self.lookup_kwarg_since: str(today + datetime.timedelta(days=1)),
                self.lookup_kwarg_until: str(today + datetime.timedelta(days=2)),
            }),
            ('pozítří', {
                self.lookup_kwarg_since: str(today + datetime.timedelta(days=2)),
                self.lookup_kwarg_until: str(today + datetime.timedelta(days=3)),
            }),
            ('popozítří', {
                self.lookup_kwarg_since: str(today + datetime.timedelta(days=3)),
                self.lookup_kwarg_until: str(today + datetime.timedelta(days=4)),
            }),
        )
        if field.null:
            self.lookup_kwarg_isnull = '%s__isnull' % field_path
            self.links += (
                (_('No date'), {self.field_generic + 'isnull': 'True'}),
                (_('Has date'), {self.field_generic + 'isnull': 'False'}),
            )
        super().__init__(field, request, params, model, model_admin, field_path)

    def expected_parameters(self):
        params = [self.lookup_kwarg_since, self.lookup_kwarg_until]
        if self.field.null:
            params.append(self.lookup_kwarg_isnull)
        return params

    def choices(self, changelist):
        for title, param_dict in self.links:
            yield {
                'selected': self.date_params == param_dict,
                'query_string': changelist.get_query_string(param_dict, [self.field_generic]),
                'display': title,
            }


@admin.register(OrderedProduct)
class OrderedProductAdmin(admin.ModelAdmin):
    list_display = ['production_link', 'next_1st_day_to_do', 'next_2nd_day_to_do', 'next_3rd_day_to_do',
                    'next_3_days_to_do', 'in_stock']
    ordering = ['-sauce', 'name']
    list_display_links = None
    list_select_related = True

    def next_1st_day_to_do(self, obj):
        return models.Item.objects.filter(
            product=obj,
            order__status__exact=models.Order.CONFIRMED,
            order__date_required__exact=datetime.date.today() + datetime.timedelta(days=1),
        ).aggregate(Sum('quantity'))['quantity__sum']

    def next_2nd_day_to_do(self, obj):
        return models.Item.objects.filter(
            product=obj,
            order__status__exact=models.Order.CONFIRMED,
            order__date_required__exact=datetime.date.today() + datetime.timedelta(days=2),
        ).aggregate(Sum('quantity'))['quantity__sum']

    def next_3rd_day_to_do(self, obj):
        return models.Item.objects.filter(
            product=obj,
            order__status__exact=models.Order.CONFIRMED,
            order__date_required__exact=datetime.date.today() + datetime.timedelta(days=3),
        ).aggregate(Sum('quantity'))['quantity__sum']

    def next_3_days_to_do(self, obj):
        return models.Item.objects.filter(
            product=obj,
            order__status__exact=models.Order.CONFIRMED,
            order__date_required__gt=datetime.date.today(),
            order__date_required__lte=datetime.date.today() + datetime.timedelta(days=3),
        ).aggregate(Sum('quantity'))['quantity__sum']

    def production_link(self, obj):
        return mark_safe(f'<a href="/admin/ffpasta/stocktransaction/add/?product={ obj.id }\
                &quantity=25&transaction_type={ models.StockTransaction.PRODUCTION }"><b>{ obj.name }</b></a>')

    production_link.short_description = 'produkt'
    next_1st_day_to_do.short_description = date_format(
        (datetime.date.today() + datetime.timedelta(days=1)), format='l, j. n.', use_l10n=True)
    next_2nd_day_to_do.short_description = date_format(
        (datetime.date.today() + datetime.timedelta(days=2)), format='l, j. n.', use_l10n=True)
    next_3rd_day_to_do.short_description = date_format(
        (datetime.date.today() + datetime.timedelta(days=3)), format='l, j. n.', use_l10n=True)
    next_3_days_to_do.short_description = 'celkem vyrobit'

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['title'] = 'Vyberte produkt k výrobě'
        return super().changelist_view(request, extra_context=extra_context)

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False


class ProductionOrderedProductAdmin(OrderedProductAdmin):

    def production_link(self, obj):
        return mark_safe(f'<a href="/produkce/ffpasta/stocktransaction/add/?product={ obj.id }\
            &quantity=25&transaction_type={ models.StockTransaction.PRODUCTION }"><b>{ obj.name }</b></a>')

    def has_module_permission(self, request):
        return True

    def has_view_permission(self, request, obj=None):
        return True


@admin.register(models.StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'datetime', 'committed_by', 'transaction_type', 'product', 'quantity']
    list_filter = ['datetime', 'transaction_type', 'committed_by']
    form = forms.StockTransactionForm

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj is not None:
            readonly_fields += ('product', 'transaction_type', 'quantity')
        return readonly_fields

    def save_model(self, request, obj, form, change):
        if obj.id is None:
            obj.committed_by = request.user
        obj.save()


class ProductionStockTransactionAdmin(StockTransactionAdmin):

    def response_add(self, request, obj, post_url_continue=None):
        return redirect('/produkce/ffpasta/orderedproduct/')

    def has_add_permission(self, request):
        return True

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return True

    def has_view_permission(self, request, obj=None):
        return True

    def has_module_permission(self, request):
        return True


class ToDoOrder(models.Order):
    class Meta:
        proxy = True
        verbose_name = 'potvrzená objednávka'
        verbose_name_plural = 'potvrzené objednávky'


class ToDoOrderAdmin(admin.ModelAdmin):
    date_hierarchy = 'date_required'
    list_display = ['__str__', 'customer_note', 'customer', 'short_date', 'my_note', 'is_complete']
    list_filter = [('date_required', ProductionFutureDateFieldFilter)]
    readonly_fields = ['datetime_ordered', 'invoiced']
    list_editable = ['my_note']
    change_form_template = 'ffpasta/admin/order_change_form.html'
    actions = ['complete']

    def short_date(self, obj):
        return obj.date_required.strftime("%d %m.")

    def is_complete(self, obj):
        return obj.status == obj.COMPLETED

    short_date.admin_order_field = 'date_required'
    short_date.short_description = 'Datum dodání'
    is_complete.admin_order_field = 'status'
    is_complete.short_description = 'Hotovo'
    is_complete.boolean = True


    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.filter(status__in=[models.Order.CONFIRMED, models.Order.COMPLETED],
                               date_required__gte=datetime.date.today(),
                               date_required__lte=(datetime.date.today() + datetime.timedelta(days=3))
                               ).order_by('date_required')

    def changelist_view(self, request, extra_context=None):
        if not request.META.get('QUERY_STRING') and (
                request.META.get('HTTP_REFERER') is None or
                request.META.get('HTTP_REFERER').split('?')[0] != request.build_absolute_uri('?')):
            return HttpResponseRedirect('?date_required__gte={}&date_required__lt={}'.format(
                datetime.date.today(), datetime.date.today() + datetime.timedelta(days=8)))
        return super().changelist_view(request, extra_context)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return True

    def has_module_permission(self, request):
        return True

    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj, change, **kwargs)
        form.clean_status = clean_status
        return form

    def get_changelist_form(self, request, **kwargs):
        form = super().get_changelist_form(request, **kwargs)
        form.clean_status = clean_status
        return form

    def save_model(self, request, obj, form, change):
        if not change:
            obj.datetime_ordered = datetime.datetime.now()
        return super().save_model(request, obj, form, change)

    def complete(self, request, queryset):
        for order in queryset:
            err_msg = order.do_complete(user=request.user)
            if err_msg:
                messages.error(request, err_msg)
            else:
                messages.info(request, f'Objednávka č. { order.id } byla zabalena')

    complete.short_description = 'zabalit'


production_admin.register(ToDoOrder, ToDoOrderAdmin)
production_admin.register(OrderedProduct, ProductionOrderedProductAdmin)
production_admin.register(models.StockTransaction, ProductionStockTransactionAdmin)
production_admin.register(TodayDeliveryOrder, ProductionTodayDeliveryOrderAdmin)
