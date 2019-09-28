from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render
from django.utils.html import mark_safe
from django.utils.crypto import get_random_string
from django.views.generic import FormView, ListView, DetailView, UpdateView
from datetime import datetime
from . import forms, models


class NoLabelSuffixMixin:
    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs.update({'label_suffix': ''})
        return form_kwargs


class Home(ListView):
    model = models.Section
    template_name = 'ffpasta/index.html'

    def get_context_data(self, *args, **kwargs):
        context_data = super().get_context_data(*args, **kwargs)
        for obj in self.object_list:
            if obj.widget:
                obj.widget_context = obj.get_widget().get_context_data(self)
        context_data['og_appId'] = settings.FB_APP_ID
        return context_data


class ContactView(FormView):
    template_name = 'ffpasta/contact.html'
    form_class = forms.ContactForm

    def form_valid(self, form):
        if form.send_mail():
            messages.add_message(self.request, messages.INFO, 'Zpráva odeslána =)')
        else:
            messages.add_message(self.request, messages.INFO, 'Zprávu se nepodařilo odeslat =(')
        return HttpResponseRedirect(self.request.POST.get('from_url'))


class LoginView(NoLabelSuffixMixin, LoginView):
    template_name = 'ffpasta/login.html'

    def get(self, request, *args, **kwargs):
        logout(request)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if request.POST.get('register'):
            return HttpResponseRedirect(f'/registrace/')
        return super().post(request, *args, **kwargs)

    def get_success_url(self):
        if len(self.request.POST.get('password')) < 8:
            return '/zmena-hesla/'
        return super().get_success_url()


class RegistrationView(NoLabelSuffixMixin, FormView):
    form_class = forms.RegistrationForm
    template_name = 'ffpasta/registration.html'

    def form_valid(self, form):
        customer = models.Customer.self_register(email=form.cleaned_data['email'],
                                                 ico=form.cleaned_data['ico'],
                                                 password=form.cleaned_data['password'])
        if customer:
            customer.send_verification_code()
            login(self.request, customer.user)
            messages.add_message(self.request, messages.INFO,
                                 "Děkujeme, za Vaši registraci.<br> Na Vaši e-mailovou adresu jsme odeslali ověřovací odkaz.")
            return HttpResponseRedirect('/nastaveni/')
        self.render_to_response(self.get_context_data(form=form))

    def post(self, request, *args, **kwargs):
        if request.POST.get('login'):
            return HttpResponseRedirect(f'/prihlaseni/')
        return super().post(request, *args, **kwargs)


class ProductDetailView(DetailView):
    model = models.Product

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['domain'] = settings.DOMAIN
        return context_data


class RecipeDetailView(DetailView):
    model = models.Product


class CustomerRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if hasattr(request.user, 'customer'):
            return super().dispatch(request, *args, **kwargs)
        elif request.user.is_staff:
            messages.add_message(request, messages.ERROR, "Pro objednávání se přihlaš jako zákazník.")
            return HttpResponseRedirect('/admin/ffpasta/order/')
        raise Http404("Zákazník nenalezen")


class VerifiedEmailRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if request.user.customer.email_is_verified:
            return super().dispatch(request, *args, **kwargs)
        else:
            return HttpResponseRedirect('/overte-svou-adresu/')


class DeliveryAddressRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if request.user.customer.delivery_addresses.all().exists():
            return super().dispatch(request, *args, **kwargs)
        else:
            messages.add_message(request, messages.INFO, "Než začnete objednávat, nastavte si doručovací adresu.")
            return HttpResponseRedirect('/nastaveni/')


class CustomerDetailView(LoginRequiredMixin, CustomerRequiredMixin, DetailView):
    model = models.Customer
    template_name = 'ffpasta/customer_detail.html'

    def get_object(self, queryset=None):
        return self.request.user.customer


class CustomerUpdateView(LoginRequiredMixin, CustomerRequiredMixin, NoLabelSuffixMixin, UpdateView):
    model = models.Customer
    fields = ['name', 'street', 'postal_code', 'city', 'same_delivery_address']
    formset_class = forms.AddressFormSet
    success_url = '/zakaznik/'

    def get_formset(self, **kwargs):
        formset = self.formset_class(queryset=self.object.delivery_addresses.all(), **kwargs)
        for form in formset:
            if form.instance.id:
                form.fields['DELETE'].is_boolean = True
                form.fields['DELETE'].label = f'{ form.instance.street }, { form.instance.postal_code } { form.instance.city }'
            else:
                form.fields['DELETE'].widget = forms.forms.HiddenInput()
        return formset

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.formset = self.get_formset()
        return super().get(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return self.request.user.customer

    def get_form(self, form_class=None):
        form = super().get_form(self.form_class)
        form.fields['name'].required = True
        form.fields['street'].required = True
        form.fields['postal_code'].required = True
        form.fields['city'].required = True
        form.fields['same_delivery_address'].is_boolean = True
        return form

    def get_context_data(self, **kwargs):
        return super().get_context_data(formset=self.formset)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        fromset_data = self.request.POST.copy()
        for i in range(int(fromset_data.get('form-TOTAL_FORMS', 6))):
            if fromset_data.get(f'form-{ i }-street'):
                fromset_data[f'form-{ i }-customer'] = str(self.object.id)
        self.formset = self.get_formset(data=fromset_data)
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        if form.cleaned_data['same_delivery_address'] is True:
            return super().form_valid(form)
        if self.formset.is_valid():
            self.object = form.save()
            self.formset.save()
            return HttpResponseRedirect(self.get_success_url())
        return self.render_to_response(self.get_context_data(form=form, formset=self.formset))


class OrderListView(LoginRequiredMixin, CustomerRequiredMixin, ListView):
    model = models.Order

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(customer=self.request.user.customer.pk, datetime_ordered__isnull=False).order_by('-date_required')


class OrderCreateUpdateView(LoginRequiredMixin, CustomerRequiredMixin, DeliveryAddressRequiredMixin, UpdateView):
    model = models.Order
    form_class = forms.OrderCreateUpdateForm
    formset_class = forms.ItemFormSet
    success_url = '/dokonceni-objednavky/'
    template_name = 'ffpasta/order_createupdate_form.html'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object:
            self.formset = self.formset_class(initial=self.object.item_set.values('product', 'quantity'))
        else:
            self.formset = self.formset_class()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if 'back_to_overview' in request.POST:
            return HttpResponseRedirect('/objednavky/')
        self.formset = self.formset_class(data=self.request.POST)
        self.initial = {'customer': self.request.user.customer.pk}
        self.object = self.get_object()
        return super().post(request, *args, **kwargs)

    def get_object(self, queryset=None):
        queryset = models.Order.objects.filter(customer=self.request.user.customer, datetime_ordered__isnull=True)
        if queryset.exists():
            return queryset.first()
        return None

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['dates'] = self.dates()
        return kwargs

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['customer'].disabled = True
        address_choices = models.Address.objects.filter(customer=self.request.user.customer)
        form.fields['address'].queryset = address_choices
        form.fields['address'].empty_label = None
        if address_choices.count() < 2:
            self.hide_addresses = True
        return form

    def get_context_data(self, **kwargs):
        return super().get_context_data(formset=self.formset)

    def dates(self):
        return {address.id: address.get_dates() for address in self.request.user.customer.delivery_addresses.all()}

    def form_valid(self, form):
        if self.formset.is_valid():
            response = super().form_valid(form)
            models.Item.objects.filter(order=self.object).delete()
            self.formset.save(self.object)
            return response
        return self.render_to_response(self.get_context_data(form=form, formset=self.formset))


class OrderFinishView(LoginRequiredMixin, CustomerRequiredMixin, DeliveryAddressRequiredMixin, VerifiedEmailRequiredMixin, UpdateView):
    model = models.Order
    fields = ['datetime_ordered']
    success_url = '/objednavky/'
    template_name = 'ffpasta/order_confirm_form.html'

    def get_object(self, queryset=None):
        queryset = models.Order.objects.filter(customer=self.request.user.customer, datetime_ordered=None)
        if queryset.exists():
            return queryset.first()
        return HttpResponseRedirect('/nova-objednavka/')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['datetime_ordered'].disabled = True
        return form

    def post(self, request, *args, **kwargs):
        if 'back_to_edit_order' in request.POST:
            return HttpResponseRedirect('/nova-objednavka/')
        self.initial = {'datetime_ordered': datetime.now()}
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        token = get_random_string(length=32)
        cache.set(f'MANAGE_TOKEN_FOR_ORDER_{ self.object.id }', token, 3600)
        self.object.send_manage_token_to_admins(token)
        return super().form_valid(form)


class ForgottenPasswordView(FormView):
    form_class = forms.ForgottenPasswordForm
    template_name = 'ffpasta/forgotten_password.html'

    def form_valid(self, form):
        user = User.objects.filter(email__exact=form.cleaned_data['email']).first()
        if user:
            token = get_random_string(length=32)
            cache.set(f'PASSWORD_RESET_TOKEN_FOR_CUSTOMER_{ user.id }', token, 600)
            if user.send_password_reset_token(token):
                messages.add_message(self.request, messages.INFO, 'Na zadanou e-mailovou adresu, jsme Vám zaslali odkaz pro obnovu hesla.')
            else:
                messages.add_message(self.request, messages.ERROR, 'Omlouváme se, ale nepodařilo se odeslat odkaz pro obnovu hesla. Kontaktujte nás, prosím, na e-mail: info@ffpasta.cz')
            return self.render_to_response(self.get_context_data())
        else:
            messages.add_message(self.request, messages.ERROR, 'Zatím nemáme žádného zákazníka s tímto emailem. Chcete-li se jím stát, <a href="/registrace/">zaregistrujte se</a> !')
            return self.render_to_response(self.get_context_data(form=form))


class ChangePasswordView(FormView):
    form_class = forms.ChangePasswordForm
    template_name = 'ffpasta/change_password.html'
    success_url = '/objednavky/'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        id = kwargs.get('id', None)
        token = kwargs.get('token', None)
        if id and token:
            if token == cache.get(f'PASSWORD_RESET_TOKEN_FOR_CUSTOMER_{ id }'):
                self.user_id = id
                return super().dispatch(request, *args, **kwargs)
            else:
                messages.add_message(self.request, messages.ERROR, mark_safe('Je nám líto, ale Vašemu tokenu vypršela platnost, Nechte si, prosím, <a href=/obnova-hesla/>zaslat nový odkaz</a> pro obnovu hesla.'))
                return self.render_to_response(self.get_context_data())
        else:
            raise Http404("Stránka nenalezena.")

    def form_valid(self, form):
        if self.request.user.is_authenticated:
            user = self.request.user
        else:
            user = User.objects.filter(id=self.user_id).first()
        if user:
            user.set_password(form.cleaned_data['password'])
            user.save()
            login(self.request, user)
            messages.add_message(self.request, messages.INFO, 'Vaše heslo bylo úspěšně změněno.')
        else:
            raise Http404("Uživatel nenalezen.")
        return super().form_valid(form)


def reject_order(request, id, token):
    if id and token:
        title = 'Objednávka NEodmítnuta'
        if token == cache.get(f'MANAGE_TOKEN_FOR_ORDER_{ id }'):
            order = models.Order.objects.filter(id=id).first()
            err_msg = order.do_reject()
            if err_msg:
                messages.add_message(request, messages.ERROR, err_msg)
            else:
                messages.add_message(request, messages.SUCCESS, f'Objednávka č. { order.id } byla úspěšně odmítnuta.')
                title = 'Objednávka odmítnuta'
        else:
            messages.add_message(request, messages.ERROR, mark_safe('Je mi líto, ale Tvému tokenu vypršela platnost.<br>Objednávku můžeš odmítnout běžným způsobem <a href=/objednavky/>v administraci</a>.'))
        return render(request, 'ffpasta/message.html', context={'title':title})
    else:
        raise Http404("Stránka nenalezena.")


def confirm_order(request, id, token):
    if id and token:
        title = 'Objednávka NEpotvrzena'
        if token == cache.get(f'MANAGE_TOKEN_FOR_ORDER_{ id }'):
            order = models.Order.objects.filter(id=id).first()
            err_msg = order.do_confirm()
            if err_msg:
                messages.add_message(request, messages.ERROR, err_msg)
            else:
                messages.add_message(request, messages.SUCCESS, f'Objednávka č. { order.id } byla úspěšně potvrzena.')
                title = 'Objednávka potvrzena'
        else:
            messages.add_message(request, messages.ERROR, mark_safe('Je mi líto, ale Tvému tokenu vypršela platnost.<br>Objednávku můžeš potvrdit běžným způsobem <a href=/objednavky/>v administraci</a>.'))
        return render(request, 'ffpasta/message.html', context={'title':title})
    else:
        raise Http404("Stránka nenalezena.")


def resend_email_verification_token(request, id):
    customer = models.Customer.objects.filter(id=id).first()
    token = cache.get(f'EMAIL_VERIFICATION_TOKEN_FOR_CUSTOMER_{ id }')
    if customer and not (customer.email_is_verified or token):
        customer.send_verification_code()
        return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
    return Http404("Stránka nenalezena.")


def verify_email(request, id, token):
    if id and token:
        customer = models.Customer.objects.filter(id=id).first()
        if customer and not customer.email_is_verified:
            if token == cache.get(f'EMAIL_VERIFICATION_TOKEN_FOR_CUSTOMER_{ id }'):
                customer.verify_email()
                login(request, user=customer.user)
                messages.add_message(request, messages.SUCCESS, mark_safe('Vaše e-mailová adresa byla úspěšně ověřena.'))
                return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
            title = 'Pozdě.'
            messages.add_message(request, messages.ERROR, mark_safe('Je nám líto, ale platnost odkazu vypršela.<br>'\
                                                                    f'<a href=/nove-overeni-emailu/{ id }/>zaslat nový odkaz</a>'))
            return render(request, 'ffpasta/message.html', context={'title': title})
    raise Http404("Stránka nenalezena.")


def email_verification_required(request):
    if request.user.is_anonymous or request.user.customer.email_is_verified:
        raise Http404("Stránka nenalezena.")
    title = 'Ověření e-mailu'
    messages.add_message(request, messages.ERROR, mark_safe('Na Váši e-mailovou adresu jsme Vám zaslali ověřovací odkaz.<br>'\
                                                            f'<a href=/nove-overeni-emailu/{ request.user.customer.id }/>zaslat nový odkaz</a>'))
    return render(request, 'ffpasta/message.html', context={'title': title})
