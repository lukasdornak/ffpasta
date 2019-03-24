import datetime

from django.contrib import admin
from django.http import HttpResponseRedirect
from django.forms import ValidationError, CharField
from django.utils.translation import gettext_lazy as _

from . import forms, models, idoklad


class PublishMixin:
    actions = ['publish', 'hide']

    def publish(self, request, queryset):
        queryset.update(published=True)

    def hide(self, request, queryset):
        queryset.update(published=False)

    publish.short_description = 'Publikovat'
    hide.short_description = 'Skrýt'


class ActiveMixin:
    actions = ['activate', 'deactivate']

    def activate(self, request, queryset):
        queryset.update(active=True)

    def deactivate(self, request, queryset):
        queryset.update(active=False)

    activate.short_description = 'Zařadit do nabídky'
    deactivate.short_description = 'Vyřadit z nabídky'



@admin.register(models.PriceCategory)
class PriceCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'default_price']


@admin.register(models.Pasta)
class PastaAdmin(ActiveMixin, PublishMixin, admin.ModelAdmin):
    list_display = ['name', 'length', 'published', 'active']
    list_filter = ['length', ]


@admin.register(models.Sauce)
class SauceAdmin(ActiveMixin, PublishMixin, admin.ModelAdmin):
    list_display = ['name', 'sauce_type', 'published', 'active']
    list_filter = ['sauce_type']


@admin.register(models.Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'monday', 'tuesday', 'wednesday', 'thursday',
                    'friday', 'saturday', 'sunday']


class PriceInline(admin.TabularInline):
    model = models.Price
    extra = 0


class HasIdIDokladFilter(admin.SimpleListFilter):
    title = 'kontakt iDokladu'
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
    list_display = ['name', 'ico', 'delivery', 'user', 'has_id_idoklad']
    list_filter = ['ico', HasIdIDokladFilter]
    actions = ['connect']
    inlines = [PriceInline, ]
    fieldsets = (
        (None, {
            'fields': ('name', 'ico', 'delivery', 'user'),
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        return ['user', 'id_idoklad'] if obj else ['id_idoklad']

    def has_id_idoklad(self, obj):
        return bool(obj.id_idoklad)

    def connect(self, request, queryset):
        idoklad.connect_customers(customers=queryset)

    connect.short_description = 'propojit s kontakty v iDokladu'
    has_id_idoklad.short_description = 'kontakt iDokladu'
    has_id_idoklad.boolean = True


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
    if self.instance.invoiced and data < 2:
        raise ValidationError('Vyfakturovanou objednávku nelze vrátit.')
    return data


@admin.register(models.Order)
class OrderAdmin(admin.ModelAdmin):
    date_hierarchy = 'date_required'
    list_display = ['__str__', 'customer_note', 'customer', 'short_datetime', 'short_date', 'invoiced', 'status', 'my_note']
    list_filter = (('date_required', FutureDateFieldFilter), 'status')
    readonly_fields = ['datetime_ordered', 'invoiced']
    list_editable = ['status', 'my_note']
    change_form_template = 'ffpasta/order_change_form.html'
    inlines = [ItemInline]

    def short_datetime(self, obj):
        return obj.datetime_ordered.strftime("%d.%m. %H:%M")

    short_datetime.admin_order_field = 'datetime_ordered'
    short_datetime.short_description = 'Objednáno'

    def short_date(self, obj):
        return obj.date_required.strftime("%d %m.")

    short_date.admin_order_field = 'date_required'
    short_date.short_description = 'Datum dodání'


    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.filter(datetime_ordered__isnull=False).order_by('date_required')

    def changelist_view(self, request, extra_context=None):
        if not request.META.get('QUERY_STRING') and (request.META.get('HTTP_REFERER') is None or request.META.get('HTTP_REFERER').split('?')[0] != request.build_absolute_uri('?')):
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


class UncommittedOrder(models.Order):
    class Meta:
        proxy = True
        verbose_name = 'neobjednaná objednávka'
        verbose_name_plural = 'neobjednané objednávky'


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

    def has_delete_permission(self, request, obj=None):
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

