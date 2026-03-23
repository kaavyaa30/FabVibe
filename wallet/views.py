from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import JsonResponse
from .services import get_or_create_wallet, apply_wallet_to_order
from decimal import Decimal


@login_required
def wallet_dashboard(request):
    wallet = get_or_create_wallet(request.user)
    transactions = wallet.transactions.select_related('order').all()[:50]
    return render(request, 'wallet/wallet_dashboard.html', {
        'wallet': wallet,
        'transactions': transactions,
    })


@login_required
def wallet_balance_api(request):
    """Returns current wallet balance as JSON (used by checkout JS)."""
    wallet = get_or_create_wallet(request.user)
    return JsonResponse({'balance': float(wallet.balance)})


@login_required
def apply_wallet_api(request):
    """
    POST: { "amount": <requested_wallet_deduction>, "order_total": <total> }
    Returns applicable wallet amount.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    import json
    data = json.loads(request.body)
    requested = Decimal(str(data.get('amount', 0)))
    order_total = Decimal(str(data.get('order_total', 0)))
    applicable = apply_wallet_to_order(request.user, requested, order_total)
    request.session['wallet_deduction'] = float(applicable)
    return JsonResponse({'applicable': float(applicable)})
