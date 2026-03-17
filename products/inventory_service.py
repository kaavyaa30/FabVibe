"""
Inventory management service for handling stock operations
"""
from django.db import transaction
from django.conf import settings
from products.models import Product, Inventory, InventoryLog


class InventoryService:
    """Service for managing product inventory"""
    
    @staticmethod
    def check_availability(product, size, quantity):
        """
        Check if requested quantity is available for a product size
        
        Args:
            product: Product instance
            size: Size string (e.g., 'M', 'L')
            quantity: Requested quantity
            
        Returns:
            tuple: (is_available: bool, available_quantity: int)
        """
        try:
            inventory = Inventory.objects.get(product=product, size=size)
            is_available = inventory.quantity >= quantity
            return is_available, inventory.quantity
        except Inventory.DoesNotExist:
            return False, 0
    
    @staticmethod
    @transaction.atomic
    def decrease_inventory(product, size, quantity, reason="Order placed"):
        """
        Decrease inventory when an order is placed
        
        Args:
            product: Product instance
            size: Size string
            quantity: Quantity to decrease
            reason: Reason for decrease (for logging)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            inventory = Inventory.objects.select_for_update().get(
                product=product, 
                size=size
            )
            
            if inventory.quantity < quantity:
                return False
            
            # Decrease inventory
            inventory.quantity -= quantity
            inventory.save()
            
            # Update product total inventory
            InventoryService._sync_product_inventory(product)
            
            # Log the change
            InventoryLog.objects.create(
                product=product,
                quantity_change=-quantity,
                reason=reason
            )
            
            return True
            
        except Inventory.DoesNotExist:
            return False
    
    @staticmethod
    @transaction.atomic
    def increase_inventory(product, size, quantity, reason="Order cancelled", admin=None):
        """
        Increase inventory when an order is cancelled or returned
        
        Args:
            product: Product instance
            size: Size string
            quantity: Quantity to increase
            reason: Reason for increase (for logging)
            admin: Admin user who made the change (optional)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            inventory = Inventory.objects.select_for_update().get(
                product=product,
                size=size
            )
            
            # Increase inventory
            inventory.quantity += quantity
            inventory.save()
            
            # Update product total inventory
            InventoryService._sync_product_inventory(product)
            
            # Log the change
            InventoryLog.objects.create(
                product=product,
                admin=admin,
                quantity_change=quantity,
                reason=reason
            )
            
            return True
            
        except Inventory.DoesNotExist:
            return False
    
    @staticmethod
    def _sync_product_inventory(product):
        """
        Sync Product.inventory field with total from Inventory table
        
        Args:
            product: Product instance
        """
        total_inventory = sum(
            inv.quantity for inv in Inventory.objects.filter(product=product)
        )
        product.inventory = total_inventory
        product.save(update_fields=['inventory'])
    
    @staticmethod
    def get_inventory_status(product, size):
        """
        Get inventory status for a product size
        
        Args:
            product: Product instance
            size: Size string
            
        Returns:
            dict: Status information including quantity, in_stock, low_stock
        """
        try:
            inventory = Inventory.objects.get(product=product, size=size)
            return {
                'quantity': inventory.quantity,
                'in_stock': inventory.is_in_stock(),
                'low_stock': inventory.is_low_stock(),
                'threshold': inventory.low_stock_threshold
            }
        except Inventory.DoesNotExist:
            return {
                'quantity': 0,
                'in_stock': False,
                'low_stock': False,
                'threshold': settings.LOW_STOCK_THRESHOLD
            }
    
    @staticmethod
    def get_product_total_inventory(product):
        """
        Get total inventory across all sizes for a product
        
        Args:
            product: Product instance
            
        Returns:
            int: Total inventory quantity
        """
        return sum(
            inv.quantity for inv in Inventory.objects.filter(product=product)
        )
    
    @staticmethod
    @transaction.atomic
    def process_order_inventory(order_items):
        """
        Process inventory decrease for all items in an order
        
        Args:
            order_items: QuerySet or list of OrderItem instances
            
        Returns:
            tuple: (success: bool, error_message: str or None)
        """
        # First check if all items are available
        for item in order_items:
            is_available, available_qty = InventoryService.check_availability(
                item.product, 
                item.size, 
                item.quantity
            )
            
            if not is_available:
                return False, f"{item.product.name} (Size: {item.size}) - Only {available_qty} available"
        
        # All items available, proceed with inventory decrease
        for item in order_items:
            success = InventoryService.decrease_inventory(
                item.product,
                item.size,
                item.quantity,
                reason=f"Order {item.order.order_id}"
            )
            
            if not success:
                # This shouldn't happen as we checked availability above
                return False, f"Failed to decrease inventory for {item.product.name}"
        
        return True, None
    
    @staticmethod
    @transaction.atomic
    def restore_order_inventory(order_items, reason="Order cancelled"):
        """
        Restore inventory for cancelled orders
        
        Args:
            order_items: QuerySet or list of OrderItem instances
            reason: Reason for restoration
            
        Returns:
            bool: True if successful
        """
        for item in order_items:
            InventoryService.increase_inventory(
                item.product,
                item.size,
                item.quantity,
                reason=f"{reason} - Order {item.order.order_id}"
            )
        
        return True
