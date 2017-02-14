from YAASapp import auction_state_updater


# possible auction states are:
# active: when auction created, stays in this state until deadline hits or is banned
# banned: if admin bans the auction
# due: if the deadline of an auction hits
# adjudicated: when a due auction has been processed basically every old auction stays in database history in this state
def update_auctions():
    auction_state_updater.update_active_auctions()
    auction_state_updater.update_due_auctions()
