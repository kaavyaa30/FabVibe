"""Wallet business logic — all wallet operations go through here."""
from decimal import Decimal
from django.db import transaction as db_transaction

SIGNUP_BONUS     = Decimal('100.00')   # ₹100 on registration
CASHBACK_PERCENT = Decimal('5')        # 5% cashback on delivery


def get_or_create_wallet(user):
    from .models import Wallet
    wallet, _ = Wallet.objects.get_or_create(user=user)
    return wallet


def award_signup_bonus(user):
    wallet = get_or_create_wallet(user)
    if wallet.balance == 0 and not wallet.transactions.exists():
        wallet.credit(SIGNUP_BONUS, "Welcome bonus — thanks for joining FabVibe!")
    return wallet


def award_cashback(order):
    """Credit 5% cashback when order is delivered."""
    wallet = get_or_create_wallet(order.user)
    cashback = (order.total_amount * CASHBACK_PERCENT / 100).quantize(Decimal('0.01'))
    if cashback > 0:
        wallet.credit(cashback, f"5% cashback on order {order.order_id}", order=order)
    return cashback


def apply_wallet_to_order(user, requested_amount, order_total):
    """
    Returns how much wallet balance can be applied.
    Cannot exceed wallet balance or order total.
    """
    wallet = get_or_create_wallet(user)
    applicable = min(wallet.balance, Decimal(str(requested_amount)), Decimal(str(order_total)))
    return applicable.quantize(Decimal('0.01'))


def debit_wallet_for_order(user, amount, order):
    wallet = get_or_create_wallet(user)
    with db_transaction.atomic():
        wallet.debit(amount, f"Payment for order {order.order_id}", order=order)


def refund_to_wallet(order, amount=None, reason="Refund"):
    """Credit refund back to wallet. Defaults to full order total."""
    wallet = get_or_create_wallet(order.user)
    refund_amount = Decimal(str(amount)) if amount else order.total_amount
    wallet.credit(refund_amount, f"{reason} for order {order.order_id}", order=order)
    return refund_amount
