"""Price calculation service for cart and checkout"""
from decimal import Decimal
from typing import Dict, Optional
from django.conf import settings


class PriceCalculator:
    """
    Centralized service for calculating cart and order prices.
    
    Handles:
    - Subtotal calculation from cart items
    - Tax calculation based on shipping address
    - Shipping charges based on order value and destination
    - Discount application
    - Final total calculation
    """
    
    # Default tax rate (18% GST)
    DEFAULT_TAX_RATE = Decimal('0.18')
    
    # Shipping configuration
    FREE_SHIPPING_THRESHOLD = Decimal('500')
    STANDARD_SHIPPING_CHARGE = Decimal('50')
    
    def __init__(self, cart, coupon_discount: Optional[Decimal] = None, shipping_address=None):
        """
        Initialize price calculator.
        
        Args:
            cart: Cart instance
            coupon_discount: Optional coupon discount amount
            shipping_address: Optional shipping address for tax calculation
        """
        self.cart = cart
        self.coupon_discount = coupon_discount or Decimal('0')
        self.shipping_address = shipping_address
        self._cache = {}
    
    def calculate_subtotal(self) -> Decimal:
        """
        Calculate subtotal from all cart items.
        
        Returns:
            Decimal: Sum of all cart item subtotals
        """
        if 'subtotal' not in self._cache:
            subtotal = sum(
                item.get_subtotal() 
                for item in self.cart.items.select_related('product').all()
            )
            self._cache['subtotal'] = Decimal(str(subtotal))
        
        return self._cache['subtotal']
    
    def calculate_tax(self, subtotal: Optional[Decimal] = None) -> Decimal:
        """
        Calculate tax based on shipping address.
        
        Currently applies a flat 18% GST rate. In the future, this can be
        enhanced to calculate state-specific tax rates based on shipping address.
        
        Args:
            subtotal: Optional subtotal to calculate tax on. If not provided,
                     calculates from cart items.
        
        Returns:
            Decimal: Tax amount
        """
        if 'tax' not in self._cache:
            if subtotal is None:
                subtotal = self.calculate_subtotal()
            
            # Apply tax rate
            tax_rate = self._get_tax_rate()
            self._cache['tax'] = subtotal * tax_rate
        
        return self._cache['tax']
    
    def calculate_shipping(self, subtotal: Optional[Decimal] = None) -> Decimal:
        """
        Calculate shipping charges based on order value and destination.
        
        Current logic:
        - Free shipping for orders over 500
        - Standard charge of 50 for orders under 500
        
        Args:
            subtotal: Optional subtotal to calculate shipping on. If not provided,
                     calculates from cart items.
        
        Returns:
            Decimal: Shipping charge amount
        """
        if 'shipping' not in self._cache:
            if subtotal is None:
                subtotal = self.calculate_subtotal()
            
            # Free shipping over threshold
            if subtotal >= self.FREE_SHIPPING_THRESHOLD:
                self._cache['shipping'] = Decimal('0')
            else:
                self._cache['shipping'] = self.STANDARD_SHIPPING_CHARGE
        
        return self._cache['shipping']
    
    def calculate_discount(self) -> Decimal:
        """
        Get discount amount.
        
        Returns:
            Decimal: Discount amount from coupon
        """
        return self.coupon_discount
    
    def calculate_total(self) -> Decimal:
        """
        Calculate final total with all components.
        
        Formula: subtotal + tax + shipping - discount
        
        Returns:
            Decimal: Final total amount
        """
        if 'total' not in self._cache:
            subtotal = self.calculate_subtotal()
            tax = self.calculate_tax(subtotal)
            shipping = self.calculate_shipping(subtotal)
            discount = self.calculate_discount()
            
            self._cache['total'] = subtotal + tax + shipping - discount
        
        return self._cache['total']
    
    def get_price_breakdown(self) -> Dict[str, Decimal]:
        """
        Get complete price breakdown.
        
        Returns:
            Dict containing:
                - subtotal: Sum of all cart items
                - tax: Tax amount
                - shipping: Shipping charge
                - discount: Coupon discount
                - total: Final total
        """
        subtotal = self.calculate_subtotal()
        tax = self.calculate_tax(subtotal)
        shipping = self.calculate_shipping(subtotal)
        discount = self.calculate_discount()
        total = self.calculate_total()
        
        return {
            'subtotal': subtotal,
            'tax': tax,
            'shipping': shipping,
            'discount': discount,
            'total': total,
        }
    
    def _get_tax_rate(self) -> Decimal:
        """
        Get tax rate based on shipping address.
        
        Currently returns default rate. Can be enhanced to support
        state-specific tax rates.
        
        Returns:
            Decimal: Tax rate as decimal (e.g., 0.18 for 18%)
        """
        # Future enhancement: Calculate state-specific tax based on shipping_address
        # For now, return default GST rate
        return self.DEFAULT_TAX_RATE
    
    def recalculate(self):
        """
        Clear cache to force recalculation on next access.
        
        Call this method when cart contents change to ensure
        calculations reflect current state.
        """
        self._cache.clear()
