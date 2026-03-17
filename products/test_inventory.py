from django.test import TestCase
from django.contrib.auth import get_user_model
from products.models import Product, Category, Inventory, InventoryLog
from products.inventory_service import InventoryService
from orders.models import Order, OrderItem
from decimal import Decimal

User = get_user_model()


class InventoryServiceTests(TestCase):
    """Tests for InventoryService"""
    
    def setUp(self):
        """Set up test data"""
        # Create user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123'
        )
        
        # Create category and product
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            description='Test description',
            price=Decimal('100.00'),
            category=self.category,
            inventory=40  # Total across all sizes
        )
        
        # Create inventory for different sizes
        self.inventory_m = Inventory.objects.create(
            product=self.product,
            size='M',
            quantity=10,
            low_stock_threshold=5
        )
        
        self.inventory_l = Inventory.objects.create(
            product=self.product,
            size='L',
            quantity=15,
            low_stock_threshold=5
        )
        
        self.inventory_xl = Inventory.objects.create(
            product=self.product,
            size='XL',
            quantity=15,
            low_stock_threshold=5
        )
    
    def test_check_availability_sufficient_stock(self):
        """Test checking availability when stock is sufficient"""
        is_available, available_qty = InventoryService.check_availability(
            self.product, 'M', 5
        )
        self.assertTrue(is_available)
        self.assertEqual(available_qty, 10)
    
    def test_check_availability_insufficient_stock(self):
        """Test checking availability when stock is insufficient"""
        is_available, available_qty = InventoryService.check_availability(
            self.product, 'M', 15
        )
        self.assertFalse(is_available)
        self.assertEqual(available_qty, 10)
    
    def test_check_availability_exact_stock(self):
        """Test checking availability when requested equals available"""
        is_available, available_qty = InventoryService.check_availability(
            self.product, 'M', 10
        )
        self.assertTrue(is_available)
        self.assertEqual(available_qty, 10)
    
    def test_check_availability_nonexistent_size(self):
        """Test checking availability for non-existent size"""
        is_available, available_qty = InventoryService.check_availability(
            self.product, 'XXL', 1
        )
        self.assertFalse(is_available)
        self.assertEqual(available_qty, 0)
    
    def test_decrease_inventory_success(self):
        """Test successful inventory decrease"""
        initial_qty = self.inventory_m.quantity
        
        success = InventoryService.decrease_inventory(
            self.product, 'M', 3, reason="Test order"
        )
        
        self.assertTrue(success)
        
        # Refresh from database
        self.inventory_m.refresh_from_db()
        self.assertEqual(self.inventory_m.quantity, initial_qty - 3)
        
        # Check product total inventory was updated
        self.product.refresh_from_db()
        self.assertEqual(self.product.inventory, 37)  # 40 - 3
        
        # Check log was created
        log = InventoryLog.objects.filter(product=self.product).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.quantity_change, -3)
        self.assertEqual(log.reason, "Test order")
    
    def test_decrease_inventory_insufficient_stock(self):
        """Test inventory decrease fails when stock insufficient"""
        success = InventoryService.decrease_inventory(
            self.product, 'M', 15  # More than available (10)
        )
        
        self.assertFalse(success)
        
        # Inventory should remain unchanged
        self.inventory_m.refresh_from_db()
        self.assertEqual(self.inventory_m.quantity, 10)
    
    def test_decrease_inventory_to_zero(self):
        """Test decreasing inventory to exactly zero"""
        success = InventoryService.decrease_inventory(
            self.product, 'M', 10  # Exact amount
        )
        
        self.assertTrue(success)
        
        self.inventory_m.refresh_from_db()
        self.assertEqual(self.inventory_m.quantity, 0)
        self.assertFalse(self.inventory_m.is_in_stock())
    
    def test_increase_inventory_success(self):
        """Test successful inventory increase"""
        initial_qty = self.inventory_m.quantity
        
        success = InventoryService.increase_inventory(
            self.product, 'M', 5, reason="Order cancelled"
        )
        
        self.assertTrue(success)
        
        # Refresh from database
        self.inventory_m.refresh_from_db()
        self.assertEqual(self.inventory_m.quantity, initial_qty + 5)
        
        # Check product total inventory was updated
        self.product.refresh_from_db()
        self.assertEqual(self.product.inventory, 45)  # 40 + 5
        
        # Check log was created
        log = InventoryLog.objects.filter(product=self.product).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.quantity_change, 5)
        self.assertEqual(log.reason, "Order cancelled")
    
    def test_increase_inventory_with_admin(self):
        """Test inventory increase with admin user logged"""
        success = InventoryService.increase_inventory(
            self.product, 'M', 5, 
            reason="Manual adjustment", 
            admin=self.user
        )
        
        self.assertTrue(success)
        
        # Check log includes admin
        log = InventoryLog.objects.filter(product=self.product).first()
        self.assertEqual(log.admin, self.user)
    
    def test_get_inventory_status_in_stock(self):
        """Test getting inventory status for in-stock item"""
        status = InventoryService.get_inventory_status(self.product, 'M')
        
        self.assertEqual(status['quantity'], 10)
        self.assertTrue(status['in_stock'])
        self.assertFalse(status['low_stock'])  # 10 > 5 threshold
        self.assertEqual(status['threshold'], 5)
    
    def test_get_inventory_status_low_stock(self):
        """Test getting inventory status for low-stock item"""
        # Reduce inventory to low stock level
        self.inventory_m.quantity = 3
        self.inventory_m.save()
        
        status = InventoryService.get_inventory_status(self.product, 'M')
        
        self.assertEqual(status['quantity'], 3)
        self.assertTrue(status['in_stock'])
        self.assertTrue(status['low_stock'])  # 3 <= 5 threshold
    
    def test_get_inventory_status_out_of_stock(self):
        """Test getting inventory status for out-of-stock item"""
        # Set inventory to zero
        self.inventory_m.quantity = 0
        self.inventory_m.save()
        
        status = InventoryService.get_inventory_status(self.product, 'M')
        
        self.assertEqual(status['quantity'], 0)
        self.assertFalse(status['in_stock'])
        self.assertFalse(status['low_stock'])
    
    def test_get_product_total_inventory(self):
        """Test getting total inventory across all sizes"""
        total = InventoryService.get_product_total_inventory(self.product)
        
        # 10 (M) + 15 (L) + 15 (XL) = 40
        self.assertEqual(total, 40)
    
    def test_process_order_inventory_success(self):
        """Test processing inventory for complete order"""
        # Create order
        order = Order.objects.create(
            user=self.user,
            shipping_address='Test Address',
            payment_method='cod',
            subtotal=Decimal('200.00'),
            total_amount=Decimal('200.00')
        )
        
        # Create order items
        item1 = OrderItem.objects.create(
            order=order,
            product=self.product,
            size='M',
            quantity=3,
            price_at_purchase=Decimal('100.00')
        )
        
        item2 = OrderItem.objects.create(
            order=order,
            product=self.product,
            size='L',
            quantity=5,
            price_at_purchase=Decimal('100.00')
        )
        
        # Process inventory
        success, error_msg = InventoryService.process_order_inventory([item1, item2])
        
        self.assertTrue(success)
        self.assertIsNone(error_msg)
        
        # Check inventory was decreased
        self.inventory_m.refresh_from_db()
        self.assertEqual(self.inventory_m.quantity, 7)  # 10 - 3
        
        self.inventory_l.refresh_from_db()
        self.assertEqual(self.inventory_l.quantity, 10)  # 15 - 5
    
    def test_process_order_inventory_insufficient_stock(self):
        """Test processing inventory fails when stock insufficient"""
        # Create order
        order = Order.objects.create(
            user=self.user,
            shipping_address='Test Address',
            payment_method='cod',
            subtotal=Decimal('200.00'),
            total_amount=Decimal('200.00')
        )
        
        # Create order item with quantity exceeding stock
        item = OrderItem.objects.create(
            order=order,
            product=self.product,
            size='M',
            quantity=15,  # More than available (10)
            price_at_purchase=Decimal('100.00')
        )
        
        # Process inventory
        success, error_msg = InventoryService.process_order_inventory([item])
        
        self.assertFalse(success)
        self.assertIn('Only 10 available', error_msg)
        
        # Check inventory was NOT decreased
        self.inventory_m.refresh_from_db()
        self.assertEqual(self.inventory_m.quantity, 10)
    
    def test_restore_order_inventory(self):
        """Test restoring inventory for cancelled order"""
        # First decrease inventory
        InventoryService.decrease_inventory(self.product, 'M', 5)
        InventoryService.decrease_inventory(self.product, 'L', 3)
        
        # Create order
        order = Order.objects.create(
            user=self.user,
            order_id='TEST-ORDER',
            shipping_address='Test Address',
            payment_method='cod',
            subtotal=Decimal('200.00'),
            total_amount=Decimal('200.00')
        )
        
        # Create order items
        item1 = OrderItem.objects.create(
            order=order,
            product=self.product,
            size='M',
            quantity=5,
            price_at_purchase=Decimal('100.00')
        )
        
        item2 = OrderItem.objects.create(
            order=order,
            product=self.product,
            size='L',
            quantity=3,
            price_at_purchase=Decimal('100.00')
        )
        
        # Restore inventory
        success = InventoryService.restore_order_inventory(
            [item1, item2], 
            reason="Order cancelled"
        )
        
        self.assertTrue(success)
        
        # Check inventory was restored
        self.inventory_m.refresh_from_db()
        self.assertEqual(self.inventory_m.quantity, 10)  # Back to original
        
        self.inventory_l.refresh_from_db()
        self.assertEqual(self.inventory_l.quantity, 15)  # Back to original


class InventoryIntegrationTests(TestCase):
    """Integration tests for inventory management"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123'
        )
        
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            description='Test description',
            price=Decimal('100.00'),
            category=self.category,
            inventory=20
        )
        
        self.inventory = Inventory.objects.create(
            product=self.product,
            size='M',
            quantity=20,
            low_stock_threshold=10
        )
    
    def test_inventory_prevents_overselling(self):
        """Test that inventory prevents overselling"""
        # Try to decrease more than available
        success = InventoryService.decrease_inventory(
            self.product, 'M', 25  # More than 20 available
        )
        
        self.assertFalse(success)
        
        # Inventory should remain unchanged
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 20)
    
    def test_inventory_log_tracks_changes(self):
        """Test that all inventory changes are logged"""
        # Decrease inventory
        InventoryService.decrease_inventory(self.product, 'M', 5, reason="Order 1")
        
        # Increase inventory
        InventoryService.increase_inventory(self.product, 'M', 2, reason="Return")
        
        # Decrease again
        InventoryService.decrease_inventory(self.product, 'M', 3, reason="Order 2")
        
        # Check logs
        logs = InventoryLog.objects.filter(product=self.product).order_by('timestamp')
        self.assertEqual(logs.count(), 3)
        
        self.assertEqual(logs[0].quantity_change, -5)
        self.assertEqual(logs[0].reason, "Order 1")
        
        self.assertEqual(logs[1].quantity_change, 2)
        self.assertEqual(logs[1].reason, "Return")
        
        self.assertEqual(logs[2].quantity_change, -3)
        self.assertEqual(logs[2].reason, "Order 2")
        
        # Final inventory should be 20 - 5 + 2 - 3 = 14
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 14)
    
    def test_low_stock_detection(self):
        """Test low stock detection"""
        # Set inventory to low stock level
        self.inventory.quantity = 8
        self.inventory.save()
        
        self.assertTrue(self.inventory.is_low_stock())
        self.assertTrue(self.inventory.is_in_stock())
        
        # Set to threshold exactly
        self.inventory.quantity = 10
        self.inventory.save()
        
        self.assertTrue(self.inventory.is_low_stock())
        
        # Set above threshold
        self.inventory.quantity = 11
        self.inventory.save()
        
        self.assertFalse(self.inventory.is_low_stock())
    
    def test_out_of_stock_detection(self):
        """Test out of stock detection"""
        # Set inventory to zero
        self.inventory.quantity = 0
        self.inventory.save()
        
        self.assertFalse(self.inventory.is_in_stock())
        self.assertFalse(self.inventory.is_low_stock())
        
        # Product should also show out of stock
        self.product.inventory = 0
        self.product.save()
        
        self.assertFalse(self.product.is_in_stock())
