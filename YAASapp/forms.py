from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

from YAASapp.validators import validate_auction_deadline
from django.utils.translation import ugettext_lazy as _

class UserCreateForm(UserCreationForm):
    username = forms.CharField(required=True, label=_("Username"))
    email = forms.EmailField(required=True, label=_("Email"))
    password1 = forms.CharField(label=(_("Password")), widget=forms.PasswordInput)
    password2 = forms.CharField(label=(_("Password again")), widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def save(self, commit=True):
        user = super(UserCreateForm, self).save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class CreateAuctionForm(forms.Form):
    title = forms.CharField(required=True, max_length=100)
    description = forms.CharField(required=True, max_length=1000)
    minimum_price = forms.FloatField(required=True, min_value=0)
    deadline = forms.DateTimeField(required=True, input_formats=['%d.%m.%Y %H:%M'],
                                   validators=[validate_auction_deadline], help_text=_("Enter date in form dd.mm.yyy hh:mm"))


class ConfirmationForm(forms.Form):
    print('form')
    #CHOICES = [(x, x) for x in (_("Yes"), _("No"))]
    #option = forms.ChoiceField(choices=CHOICES)

