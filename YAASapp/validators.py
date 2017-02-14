from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.utils import timezone


def validate_auction_deadline(input_date):
    # the minimum uptime for an auction is 72hours
    # that in seconds is:
    minimum_duration = 72 * 60 * 60

    # calculate the suggested auction duration in seconds
    auction_duration = (input_date - timezone.now()).total_seconds()

    if auction_duration < minimum_duration:
        raise ValidationError(
            'The Auction must be up at least 72 hours'
        )


# def validate_bid(input_bid):
