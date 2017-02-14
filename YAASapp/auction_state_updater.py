from django.core import mail
from django.utils import timezone

from YAASapp import models


def update_active_auctions():
    # check active auctions
    active_auctions = models.Auction.objects.filter(state='active')
    if len(active_auctions) > 0:
        for active_auction in active_auctions:
            deadline = active_auction.deadline

            if timezone.now() > deadline:
                active_auction.state = 'due'
                active_auction.save()


def update_due_auctions():
    # check due auctions
    due_auctions = models.Auction.objects.filter(state='due')
    if len(due_auctions) > 0:
        for due_auction in due_auctions:
            # get all the bids made in this auction
            bids = models.Bid.objects.filter(auction=due_auction)
            if len(bids) > 0:
                bidder_list = []
                for bid in bids:
                    bidder_list.append(models.User.objects.get(username=bid.bidder))

                # email all the bidders that the auction has ended
                for bidder in bidder_list:
                    # if bidder won the auction
                    if bidder_list.index(bidder) == 0:
                        send_email(bidder.email, 'Auction you bid to has ended',
                                         'Dear {}, the auction for {} has ended. You won the auction! Congratulations!'
                                         ' Thank you for participating!'
                                         .format(bidder.username, due_auction.title))
                    # if bidder didn't win
                    else:
                        send_email(bidder.email, 'Auction you bid to has ended',
                                         'Dear {}, the auction for {} has ended. Unfortunately you did not win this time. '
                                         'Thank you for participating!'
                                         .format(bidder.username, due_auction.title))

            # inform the seller
            seller = models.User.objects.filter(username=due_auction.seller)

            send_email(seller[0].email, 'Your auction has ended',
                             'Dear {}, your auction for {} has ended.'
                             .format(seller[0].username, due_auction.title))

            due_auction.state = 'adjudicated'
            due_auction.save()


def send_email(email_to, title, body):
    email_from = 'noreply@yaas.com'

    mail.send_mail(title, body, email_from, [email_to], fail_silently=False)