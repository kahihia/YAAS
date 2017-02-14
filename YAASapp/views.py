import calendar

from datetime import datetime

from django.forms import Form
from django.utils.translation import gettext_lazy as _

from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone

from django.contrib import auth
from django.contrib.auth.decorators import login_required
from django.core import mail
from django.shortcuts import render, render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.views import View

from YAASapp import auction_state_updater
from YAASapp import cronjobs
from YAASapp import oer_handler
from YAASapp.forms import *
from YAASapp import models


def index(request):
    return render(request, "index.html")


def view_profile(request):
    if not request.user.is_authenticated():
        messages.add_message(request, messages.ERROR, _("You must be logged in to use this feature."))
        return HttpResponseRedirect('/login/?next=%s' % request.path)

    if request.method == 'POST':
        change_request = request.POST.get('change_request', '')

        # if change email
        if change_request == 'email':
            request.user.email = request.POST.get('new_email', '');
            request.user.save()

        # if change password
        else:
            # if the new passwords don't match
            if request.POST.get('new_password1', '1') != request.POST.get('new_password2', '2'):
                messages.add_message(request, messages.ERROR, _("New passwords don't match"))
            else:
                # change epassword
                request.user.set_password(request.POST.get('new_password1', ''));
                request.user.save()

    return render(request, "view_profile.html")


def register(request):
    # if the user has just come back from registration form
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        print(form)
        if form.is_valid():
            # save the new user in database
            new_user = form.save()
            new_user.email = request.POST.get('email')
            new_user.save()

            messages.add_message(request, messages.INFO, _("New User is created. Please Login"))

            return HttpResponseRedirect(reverse('login'))
        else:
            form = UserCreateForm(request.POST)
    # if the user wants to create a new account
    else:
        form = UserCreateForm()

    return render(request, "registration/register.html", {'form': form})


@method_decorator(login_required, name='dispatch')
class CreateAuction(View):
    template_name = 'create_auction.html'

    # create the create_auction form
    def get(self, request):
        form = CreateAuctionForm()
        currency = get_currency(request)

        return render(request, self.template_name, {'form': form, 'currency': currency})

    def post(self, request):
        form = CreateAuctionForm(request.POST)
        currency = get_currency(request)
        if form.is_valid():
            # save the new auction
            cleaned_data = form.cleaned_data
            auction_title = cleaned_data['title']
            auction_description = cleaned_data['description']
            auction_min_price = float(cleaned_data['minimum_price'])
            auction_deadline = cleaned_data['deadline']

            auction_deadline_in_seconds = calendar.timegm(auction_deadline.timetuple())

            form = Form()

            # open the confirmation form
            return render(request, 'confirmation.html', {'form': form,
                                                         'auction_title': auction_title,
                                                         'auction_description': auction_description,
                                                         'auction_min_price': auction_min_price,
                                                         'auction_deadline': auction_deadline_in_seconds
                                                         })
        else:
            # form was invalid, need to send it back for the user to fix
            return render(request, self.template_name, {'form': form, 'currency': currency})


def save_auction(request):
    title = request.POST.get('auction_title', '')
    description = request.POST.get('auction_description', '')
    seller = request.user.username
    min_price = request.POST.get('auction_minimum_price', '')
    # change price to be saved in euros
    min_price_in_euro = oer_handler.get_price(min_price, get_currency(request), 'EUR')
    deadline = request.POST.get('auction_deadline', '')

    deadline_as_date = datetime.fromtimestamp(float(deadline))
    timezone_deadline = timezone.make_aware(deadline_as_date, timezone.get_current_timezone())
    state = 'active'

    new_auction = models.Auction(title=title, description=description, seller=seller,
                                 minimum_price=min_price_in_euro, deadline=timezone_deadline, state=state)
    new_auction.save()

    messages.add_message(request, messages.INFO, _("New Auction has been saved"))

    # send the confirmation email
    send_email(request.user.email, 'Auction created',
               'Dear {}, this is a confirmation email that you have just created a new auction called {}.'
               .format(request.user.username, title))
    return HttpResponseRedirect(reverse("browse"))


def send_email(email_to, title, body):
    email_from = 'noreply@yaas.com'

    mail.send_mail(title, body, email_from, [email_to], fail_silently=False)


def get_highest_bid(auction):
    all_bids = models.Bid.objects.filter(auction=auction)
    if len(all_bids) > 0:
        return all_bids[0]
    else:
        return 0


def has_bids(auction):
    return len(models.Bid.objects.filter(auction=auction)) != 0


def browse(request):
    if request.method == 'POST':
        search_word = request.POST.get('search')
        auctions = models.Auction.objects.filter(title__contains=search_word)
    else:
        auctions = models.Auction.objects.all()

    return render(request, 'browse.html', {'auctions': auctions})


def browse_auction(request, id):
    auction = models.Auction.objects.get(pk=id)
    if auction.state == 'active':
        currency = get_currency(request)
        highest_bid = get_highest_bid(auction)
        if highest_bid != 0:
            highest_bid = highest_bid.amount
        min_price_in_currency = oer_handler.get_price(auction.minimum_price, 'EUR', currency)
        highest_bid_in_currency = oer_handler.get_price(highest_bid, 'EUR', currency)

        return render(request, 'browse_auction.html', {'auction': auction,
                                                       'highest_bid': get_highest_bid(auction),
                                                       'exchanged_min_price': min_price_in_currency,
                                                       'exchanged_highest_bid': highest_bid_in_currency,
                                                       'currency': currency})
    else:
        messages.add_message(request, messages.ERROR, _("Your requested auction is not Active!!"))


@method_decorator(login_required, name='dispatch')
class EditAuction(View):

    def get(self, request, id):
        auction = models.Auction.objects.get(pk=id)

        if auction.state == 'active':
            if request.user.username == auction.seller:
                return render(request, 'edit_auction.html', {'auction': auction,
                                                             'highest_bid': get_highest_bid(auction)})
            messages.add_message(request, messages.ERROR, _("You can't edit an auction you're not selling."))
            return HttpResponseRedirect(reverse('browse'))
        else:
            messages.add_message(request, messages.ERROR, _("Your requested auction is not Active!!"))
            return HttpResponseRedirect(reverse('browse'))

    def post(self, request, id):
        auction = models.Auction.objects.get(pk=id)
        auction.description = request.POST.get('description')
        auction.save()
        messages.add_message(request, messages.INFO, _('Description edited'))
        return render(request, 'browse_auction.html', {'auction': auction})


@method_decorator(login_required, name='dispatch')
class BidAuction(View):

    def get(self, request, id):
        auction = models.Auction.objects.get(pk=id)
        currency = get_currency(request)
        highest_bid = get_highest_bid(auction)
        if highest_bid != 0:
            highest_bid = highest_bid.amount
        min_price_in_currency = oer_handler.get_price(auction.minimum_price, 'EUR', currency)
        highest_bid_in_currency = oer_handler.get_price(highest_bid, 'EUR', currency)

        if auction.state == 'active':
            # if seller tries to bid his own item
            if request.user.username == auction.seller:
                messages.add_message(request, messages.ERROR, _("You can't bid on an auction you're selling."))
                return HttpResponseRedirect(reverse('browse'))

            # if user is already the highest bidder
            highest_bid = get_highest_bid(auction)
            if has_bids(auction):
                if highest_bid.bidder.username == request.user.username:
                    messages.add_message(request, messages.ERROR,
                                         _("You already have the highest bid, you can't bid higher!"))
                    return HttpResponseRedirect(reverse('browse'))

            # otherwise just show the bid form to user
            return render(request, 'bid_auction.html', {'auction': auction,
                                                        'highest_bid': get_highest_bid(auction),
                                                        'exchanged_min_price': min_price_in_currency,
                                                        'exchanged_highest_bid': highest_bid_in_currency,
                                                        'currency': currency})
        else:
            messages.add_message(request, messages.ERROR, _("Your requested auction is not Active!!"))

    def post(self, request, id):
        new_bid = request.POST.get('new_bid')
        auction = models.Auction.objects.get(pk=id)
        currency = get_currency(request)
        highest_bid = get_highest_bid(auction)
        if highest_bid != 0:
            highest_bid = highest_bid.amount
        min_price_in_currency = oer_handler.get_price(auction.minimum_price, 'EUR', currency)
        highest_bid_in_currency = oer_handler.get_price(highest_bid, 'EUR', currency)

        boolean_has_bids = has_bids(auction)

        # check if description has changed
        old_description = request.POST.get('old_description')
        if old_description != auction.description:
            messages.add_message(request, messages.ERROR,
                                 _("The seller has changed description. Please bid again."))
            return render(request, 'bid_auction.html', {'auction': auction,
                                                        'highest_bid': get_highest_bid(auction),
                                                        'exchanged_min_price': min_price_in_currency,
                                                        'exchanged_highest_bid': highest_bid_in_currency,
                                                        'currency': currency
                                                        })

        # check there is no more than two decimals
        if len(new_bid.rsplit('.')[-1]) > 2:
            messages.add_message(request, messages.ERROR,
                                 _("You must have a . separator and no more than two decimals, example: '1.43'"))
            return render(request, 'bid_auction.html', {'auction': auction,
                                                        'highest_bid': get_highest_bid(auction),
                                                       'exchanged_min_price': min_price_in_currency,
                                                       'exchanged_highest_bid': highest_bid_in_currency,
                                                       'currency': currency})

        new_bid_as_float = float(new_bid)

        # the new bid must be greater than current bid
        required_bid = 0
        if highest_bid == 0:
            required_bid = min_price_in_currency
        else:
            required_bid = highest_bid_in_currency + 0.01

        # if the suggested new bid is legal
        if new_bid_as_float >= required_bid:
            # catch the old bidder so we can mail him too
            if boolean_has_bids:
                old_bidder = get_highest_bid(auction).bidder

            # delete all the earlier bids done by same user in the same auction
            models.Bid.objects.filter(auction=auction, bidder=request.user).delete()

            # update the info in database
            amount_in_euro = oer_handler.get_price(new_bid_as_float, currency, 'EUR')
            models.Bid(bidder=request.user, amount=amount_in_euro, auction=auction).save()

            # send email to old_bidder, current user and seller
            seller = User.objects.get(username=auction.seller)
            # send an email to the seller
            send_email(seller.email, 'An item you are selling has been bid on',
                       'Dear {}, your item {} has been bid by {}. The highest bid is now {}.'
                       .format(auction.seller, auction.title, request.user.username, new_bid))
            # send an email to the old bidder
            if boolean_has_bids:
                old_bidder = User.objects.get(username=old_bidder)
                send_email(old_bidder.email, 'An item you bid has been bid on',
                           'Dear {}, {} has bid item {} You no longer hold the highest bid on this item. The highest bid is now {}.'
                           .format(old_bidder.username, request.user.username, auction.title, new_bid))
            # send an email to the seller
            send_email(request.user.email, 'You have bid on an item',
                       'Dear {}, you have bid on item {}. The highest bid is now {}.'
                       .format(request.user.username, auction.title, new_bid))

            messages.add_message(request, messages.INFO, _('bid registered'))
            return HttpResponseRedirect(reverse('browse'))

        messages.add_message(request, messages.ERROR,
                             _('The new bid must be at least 0.01 more than the current bid or minimum bid'))
        return render(request, 'bid_auction.html', {'auction': auction, 'highest_bid': get_highest_bid(auction)})


@staff_member_required
def ban_auction(request, id):
    auction = models.Auction.objects.get(pk=id)
    auction.state = 'banned'
    auction.save()

    return HttpResponseRedirect(reverse('browse'))


def change_language(request):
    return render(request, 'change_language.html')


def change_currency(request):
    if request.method == 'POST':
        redirect_response = HttpResponseRedirect(reverse('index'))
        new_currency = request.POST.get('currency')
        redirect_response.set_cookie('currency', new_currency)
        messages.add_message(request, messages.INFO, _('Currency changed to: {}') .format(new_currency))
        return redirect_response

    current_currency = get_currency(request)

    currencies = {'EUR', 'USD', 'GBP'}
    return render(request, 'change_currency.html', {'currencies': currencies, 'current_currency': current_currency})


def get_currency(request):
    # default currency is EUR
    current_currency = 'EUR'
    if 'currency' in request.COOKIES:
        current_currency = request.COOKIES['currency']

    return current_currency
