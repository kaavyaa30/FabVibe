"""
Custom template filters for currency formatting
"""
from django import template

register = template.Library()


@register.filter(name='inr')
def format_inr(value):
    """
    Format a number as Indian Rupees.
    
    Usage: {{ price|inr }}
    Output: ₹1,234.56
    """
    try:
        # Convert to float if it's a string or Decimal
        amount = float(value)
        
        # Format with Indian numbering system (lakhs and crores)
        # For simplicity, using standard comma formatting
        formatted = f"₹{amount:,.2f}"
        
        return formatted
    except (ValueError, TypeError):
        return value


@register.filter(name='inr_whole')
def format_inr_whole(value):
    """
    Format a number as Indian Rupees without decimals.
    
    Usage: {{ price|inr_whole }}
    Output: ₹1,234
    """
    try:
        amount = float(value)
        formatted = f"₹{amount:,.0f}"
        return formatted
    except (ValueError, TypeError):
        return value
