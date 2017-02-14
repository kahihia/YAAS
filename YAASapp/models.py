from django.contrib.auth.models import User
from django.db import models

# Create your models here.


class Auction(models.Model):
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=1000)
    seller = models.CharField(max_length=100)
    minimum_price = models.FloatField()
    deadline = models.DateTimeField()
    state = models.CharField(max_length=50)

    # tell the model how to print an auction
    def __unicode__(self):
        return self.title


class Bid(models.Model):
    amount = models.FloatField()
    bidder = models.ForeignKey(User, on_delete=models.CASCADE)
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE)

    # tell the model how to print an auction
    def __unicode__(self):
        return 'amount: {} bidder: {} in {}' .format(self.amount, self.bidder.username, self.auction.title)

    class Meta:
        # order the bids according to amount in descending order
        ordering = ['-amount']
