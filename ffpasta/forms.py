import json

from django import forms
from django.core.exceptions import ValidationError
from django.core.mail import send_mail

from django.contrib.auth.models import User
from . import models


class ProductChoiceIterator(forms.models.ModelChoiceIterator):

    def __iter__(self):
        if self.field.empty_label is not None:
            yield ("", self.field.empty_label)
        queryset = self.queryset
        groups = (('krátké těstoviny', [self.choice(obj) for obj in queryset.filter(pasta__length=0, active=True)]),
                  ('dlouhé těstoviny', [self.choice(obj) for obj in queryset.filter(pasta__length=1, active=True)]),
                  ('hořčice a pesta', [self.choice(obj) for obj in queryset.filter(pasta__isnull=True, active=True)]))
        for group in groups:
            yield group


class ProductChoiceField(forms.ModelChoiceField):
    iterator = ProductChoiceIterator


class OrderCreateUpdateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.dates = kwargs.pop('dates', None)
        super().__init__(*args, **kwargs)

    class Meta:
        model = models.Order
        fields = ['customer', 'address', 'date_required', 'customer_note']

    def clean_date_required(self):
        address = self.cleaned_data.get('address')
        data = self.cleaned_data.get('date_required')
        if self.dates and str(data) not in self.dates[address.id]:
            raise ValidationError('Na požadované datum, není naplánován závoz.')
        return data


def clean(self):
    pasta_quantity = 0
    if not hasattr(self, 'cleaned_data'):
        raise ValidationError('Opravte prosím, níže uvedené chyby.')
    for form in self.cleaned_data:
        if hasattr(form['product'], 'pasta') and not form.get('DELETE', None):
            pasta_quantity += form['quantity']
    if 0 < pasta_quantity < 5:
        raise ValidationError('Minimální množství těstovin je 5kg')


class ContactForm(forms.Form):
    email = forms.EmailField(label='E-mail')
    name = forms.CharField(label='Jméno', max_length=50)
    message = forms.CharField(label='Zpráva',
                              widget=forms.Textarea(attrs={'width': "100%", 'cols': "80", 'rows': "5", }))
    from_url = forms.HiddenInput()

    def send_mail(self):
        message = f"Jméno: { self.cleaned_data['name'] }\n\n" \
                  f"E-mail: { self.cleaned_data['email'] }\n\n" \
                  f"Dotaz: { self.cleaned_data['message'] }"
        return send_mail(
            subject='Dotaz',
            message=message,
            from_email='admin@ffpasta.cz',
            recipient_list=['info@ffpasta.cz', ],
        )


class CustomerAdminForm(forms.ModelForm):
    user = forms.EmailField(label='E-mail')

    class Meta:
        model = models.Customer
        fields = ['name', 'ico', 'user']

    def clean_user(self):
        data = self.cleaned_data.get('user')
        if models.Customer.objects.filter(user__email=data).exists():
            raise ValidationError('Zákazník s tímto e-mailem již existuje.')
        return data

    def clean(self):
        if 'user' in self.cleaned_data:
            email = self.cleaned_data.get('user')
            user = User.objects.filter(email=email).first()
            if user:
                self.cleaned_data['user'] = user.id
            else:
                password = User.objects.make_random_password(length=6)
                user = User.objects.create_user(email, password)
                message = f'Dobrý den,\n\nvytvořili jsme Vám přístup do našeho objednávkového systému.\n' \
                          f'Pro přihlášení použijte svou e-mailovou adresu:\n\n{ user.email }\n\na heslo:\n\n' \
                          f'{ password }\n\nPo přihlášení budete vyzváni k nastavení nového hesla.\n\n' \
                          f's přáním pěknéh dne\nVáš tým FFpasta.cz'
                user.email_user(subject='registrace FFpasta', message=message, from_email='info@ffpasta.cz')
                self.cleaned_data['user'] = user.id
        return super().clean()


def save(self, order):
    for form in self.cleaned_data:
        models.Item.objects.create(order=order, product=form['product'], quantity=form['quantity'])


class ItemForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_required_attribute = True

    product = ProductChoiceField(queryset=models.Product.objects.all())
    quantity = forms.IntegerField(max_value=250, min_value=1)
    use_required_attribute = True


ItemFormSet = forms.formset_factory(form=ItemForm, extra=0, min_num=1, max_num=10, validate_max=True, validate_min=True)
ItemFormSet.clean = clean
ItemFormSet.save = save


class AddressForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, label_suffix='', **kwargs)
        self.fields['customer'].widget = forms.HiddenInput()
        if self.instance.id:
            self.fields['street'].widget = forms.HiddenInput()
            self.fields['postal_code'].widget = forms.HiddenInput()
            self.fields['city'].widget = forms.HiddenInput()

    class Meta:
        model = models.Address
        fields = ('customer', 'street', 'postal_code', 'city')


AddressFormSet = forms.modelformset_factory(model=models.Address, form=AddressForm, extra=1, min_num=1, max_num=5,
                                            validate_min=True, validate_max=True, can_delete=True)


class ItemAdminForm(forms.ModelForm):
    product = ProductChoiceField(queryset=models.Product.objects.all())
    quantity = forms.IntegerField(max_value=1000, min_value=1)

    class Meta:
        model = models.Item
        fields = ('product', 'quantity', 'unit_price')


ItemAdminFormSet = forms.inlineformset_factory(models.Order, models.Item, form=ItemAdminForm, extra=1)


class ForgottenPasswordForm(forms.Form):
    email = forms.EmailField(label='Zadejte e-mail, který používáte pro přhlášení')


class ChangePasswordForm(forms.Form):
    password = forms.CharField(label='Zadejte, prosím, nové heslo', max_length=64, min_length=8, widget=forms.PasswordInput)
    password1 = forms.CharField(label='a ještě jednou pro kontrolu', max_length=64, min_length=8, widget=forms.PasswordInput)

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data['password'] == cleaned_data['password1']:
            return cleaned_data
        else:
            raise ValidationError('Hesla se neshodují')


class StockTransactionForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.fields.get('transaction_type'):
            self.fields['transaction_type'].choices = [models.StockTransaction.TYPE_CHOICES[0], models.StockTransaction.TYPE_CHOICES[2]]

    class Meta:
        model = models.StockTransaction
        exclude = []


class PriceAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.fields.get('product'):
            self.fields['product'].choices = [(None, '---------')]
            self.fields['product'].choices += [(product.id, product.name) for product in models.Product.objects.filter(price_category__isnull=True)]

    class Meta:
        model = models.Item
        exclude = ('customer',)


class RegistrationForm(forms.Form):
    email = forms.EmailField(label='E-mail', required=True)
    ico = forms.DecimalField(label='IČ', max_digits=8, required=True)
    password = forms.CharField(label='Heslo', max_length=64, min_length=8, widget=forms.PasswordInput, required=True)
    password1 = forms.CharField(label='Ověření hesla', max_length=64, min_length=8, widget=forms.PasswordInput, required=True)

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError('Uživatel s tímto emailem již existuje.')
        return email

    def clean_ico(self):
        ico = self.cleaned_data['ico']
        if models.Customer.objects.filter(ico=ico).exists():
            raise ValidationError('Zákazník s tímto ičem je již registrován.')
        return ico

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data['password'] != cleaned_data['password1']:
            raise ValidationError('Hesla se neshodují')
        return cleaned_data
