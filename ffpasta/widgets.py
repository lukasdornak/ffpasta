from django import forms

from . import models


class Widget:
    def __init__(self, template_name=None, get_context_data=None, short_name=None, name=None):
        if template_name is not None:
            self.template_name = template_name
        if get_context_data is not None:
            self.get_context_data = get_context_data
        if short_name is not None:
            self.short_name = short_name
        if name is not None:
            self.name = name

    template_name = None
    get_context_data = None
    short_name = None
    name = None

    @classmethod
    def get_choices(cls):
        choices = [(sub_cls.short_name, sub_cls.get_name()) for sub_cls in cls.__subclasses__()]
        return tuple(choices)

    @classmethod
    def get_class(cls, short_name):
        for sub_cls in cls.__subclasses__():
            if sub_cls.short_name == short_name:
                return sub_cls

    @classmethod
    def get_name(cls):
        if cls.name:
            return cls.name
        return cls.__class__.__name__


class ItemsWidget(Widget):
    name = 'Produkty'
    short_name = 'i'
    template_name = 'ffpasta/widgets/items.html'

    def get_context_data(self):
        context_data = {
            'short_pasta_list': models.Pasta.objects.filter(length=models.Pasta.SHORT, published=True),
            'long_pasta_list': models.Pasta.objects.filter(length=models.Pasta.LONG, published=True),
            'sauce_list': models.Sauce.objects.filter(published=True)
        }
        return context_data


class DifferenceWidget(Widget):
    name = 'Rozdíly'
    short_name = 'r'
    template_name = 'ffpasta/widgets/reasons.html'

    def get_context_data(self):
        context_data = {
            'object_list': models.Difference.objects.filter(published=True)
        }
        return context_data


class ContactForm(forms.Form):
    email = forms.EmailField(label='E-mail')
    name = forms.CharField(label='Jméno', max_length=50)
    message = forms.CharField(label='Zpráva', widget=forms.Textarea(attrs={'width':"100%", 'cols' : "80", 'rows': "5", }))
    from_url = forms.HiddenInput()

    def send_mail(self):
        message = 'Jméno: {}\n\nE-mail: {}\n\nDotaz: {}'.format(self.cleaned_data['name'], self.cleaned_data['email'], self.cleaned_data['message'])
        print(message)
        # return send_mail(
        #     subject='Dotaz',
        #     message=message,
        #     from_email='admin@ffpasta.cz',
        #     recipient_list=['lukasdornak@gmail.com', ],
        # )
        return True


class ContactWidget(Widget):
    name = 'Kontakt'
    short_name = 'c'
    template_name = 'ffpasta/widgets/contact.html'

    def get_context_data(self):
        context_data = {
            'form' : ContactForm()
        }
        return context_data
