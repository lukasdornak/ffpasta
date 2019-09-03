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
from django.views.generic import FormView, ListView, DetailView, UpdateView, CreateView
from datetime import datetime, date, timedelta
from . import forms, models

from django.db.models import OuterRef, Subquery, Sum, Q


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


class LoginView(LoginView):
    template_name = 'ffpasta/login.html'
    registration_form = forms.RegistrationForm

    def get(self, request, *args, **kwargs):
        logout(request)
        return super().get(request, *args, **kwargs)

class UserCreateView(CreateView):
    model = User
    template_name = 'ffpasta/login.html'


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


class OrderListView(LoginRequiredMixin, CustomerRequiredMixin, ListView):
    model = models.Order

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(customer=self.request.user.customer.pk, datetime_ordered__isnull=False).order_by('-date_required')


class OrderCreateUpdateView(LoginRequiredMixin, CustomerRequiredMixin, UpdateView):
    model = models.Order
    form_class = forms.OrderCreateUpdateForm
    formset_class = forms.ItemFormSet
    success_url = '/dokonceni-objednavky/'
    template_name = 'ffpasta/order_createupdate_form.html'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object:
            self.formset = self.formset_class(initial=models.Item.objects.filter(order=self.object).values('product', 'quantity'))
        else:
            self.formset = self.formset_class()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if 'back_to_overview' in request.POST:
            return HttpResponseRedirect('/objednavky/')
        self.formset = self.formset_class(data = self.request.POST)
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
        return form

    def get_context_data(self, **kwargs):
        return super().get_context_data(formset=self.formset)

    def dates(self):
        return self.request.user.customer.get_dates()

    def form_valid(self, form):
        if self.formset.is_valid():
            response = super().form_valid(form)
            models.Item.objects.filter(order=self.object).delete()
            self.formset.save(self.object)
            return response
        return self.render_to_response(self.get_context_data(form=form, formset=self.formset))


class OrderFinishView(LoginRequiredMixin, CustomerRequiredMixin, UpdateView):
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
            messages.add_message(self.request, messages.ERROR, 'Zatím nemáme žádného zákazníka s tímto emailem. Chcete-li se jím stát, napište nám!')
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
