from django.db import models
from django.conf import settings
from decimal import Decimal


class Wallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} — ₹{self.balance}"

    def credit(self, amount, description, order=None):
        amount = Decimal(str(amount))
        self.balance += amount
        self.save(update_fields=['balance', 'updated_at'])
        WalletTransaction.objects.create(
            wallet=self, txn_type='credit', amount=amount,
            description=description, order=order,
            balance_after=self.balance,
        )

    def debit(self, amount, description, order=None):
        amount = Decimal(str(amount))
        if self.balance < amount:
            raise ValueError("Insufficient wallet balance")
        self.balance -= amount
        self.save(update_fields=['balance', 'updated_at'])
        WalletTransaction.objects.create(
            wallet=self, txn_type='debit', amount=amount,
            description=description, order=order,
            balance_after=self.balance,
        )

    class Meta:
        db_table = 'wallets'


class WalletTransaction(models.Model):
    TXN_TYPES = [
        ('credit', 'Credit'),
        ('debit',  'Debit'),
    ]
    wallet      = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    txn_type    = models.CharField(max_length=10, choices=TXN_TYPES)
    amount      = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255)
    order       = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, null=True, blank=True)
    balance_after = models.DecimalField(max_digits=10, decimal_places=2)
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.txn_type} ₹{self.amount} — {self.description}"

    class Meta:
        db_table = 'wallet_transactions'
        ordering = ['-created_at']
