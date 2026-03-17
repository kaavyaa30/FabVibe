from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Category, Product, ProductImage, ProductSize, ProductColor, Inventory, InventoryLog

User = get_user_model()


class CategoryModelTest(TestCase):
    """Test Category model"""
    
    def test_category_creation(self):
        """Test creating a category with name and slug"""
        category = Category.objects.create(name="Men's Clothing")
        self.assertEqual(category.name, "Men's Clothing")
        self.assertEqual(category.slug, "mens-clothing")
        self.assertIsNone(category.parent)
    
    def test_subcategory_creation(self):
        """Test creating a subcategory with parent"""
        parent = Category.objects.create(name="Men")
        subcategory = Category.objects.create(name="Shirts", parent=parent)
        self.assertEqual(subcategory.parent, parent)
        self.assertIn(subcategory, parent.subcategories.all())


class ProductModelTest(TestCase):
    """Test Product model"""
    
    def setUp(self):
        self.category = Category.objects.create(name="T-Shirts")
    
    def test_product_creation(self):
        """Test creating a product with required fields"""
        product = Product.objects.create(
            name="Cotton T-Shirt",
            category=self.category,
            description="Comfortable cotton t-shirt",
            price=29.99,
            brand="FabVibe",
            material="100% Cotton",
            care_instructions="Machine wash cold"
        )
        self.assertEqual(product.name, "Cotton T-Shirt")
        self.assertEqual(product.slug, "cotton-t-shirt")
        self.assertEqual(product.category, self.category)
        self.assertEqual(product.price, 29.99)


class InventoryModelTest(TestCase):
    """Test Inventory model"""
    
    def setUp(self):
        self.category = Category.objects.create(name="Shirts")
        self.product = Product.objects.create(
            name="Test Shirt",
            category=self.category,
            description="Test description",
            price=39.99
        )
    
    def test_inventory_creation(self):
        """Test creating inventory for a product size"""
        inventory = Inventory.objects.create(
            product=self.product,
            size="M",
            quantity=50,
            low_stock_threshold=10
        )
        self.assertEqual(inventory.product, self.product)
        self.assertEqual(inventory.size, "M")
        self.assertEqual(inventory.quantity, 50)
        self.assertTrue(inventory.is_in_stock())
        self.assertFalse(inventory.is_low_stock())
    
    def test_low_stock_detection(self):
        """Test low stock threshold detection"""
        inventory = Inventory.objects.create(
            product=self.product,
            size="L",
            quantity=5,
            low_stock_threshold=10
        )
        self.assertTrue(inventory.is_low_stock())
        self.assertTrue(inventory.is_in_stock())
    
    def test_out_of_stock(self):
        """Test out of stock detection"""
        inventory = Inventory.objects.create(
            product=self.product,
            size="XL",
            quantity=0
        )
        self.assertFalse(inventory.is_in_stock())
        self.assertFalse(inventory.is_low_stock())


class ProductImageModelTest(TestCase):
    """Test ProductImage model"""
    
    def setUp(self):
        self.category = Category.objects.create(name="Jeans")
        self.product = Product.objects.create(
            name="Blue Jeans",
            category=self.category,
            description="Classic blue jeans",
            price=59.99
        )
    
    def test_product_image_creation(self):
        """Test creating a product image"""
        image = ProductImage.objects.create(
            product=self.product,
            image="products/test.jpg",
            is_primary=True
        )
        self.assertEqual(image.product, self.product)
        self.assertTrue(image.is_primary)


class ProductSizeModelTest(TestCase):
    """Test ProductSize model"""
    
    def setUp(self):
        self.category = Category.objects.create(name="Pants")
        self.product = Product.objects.create(
            name="Chinos",
            category=self.category,
            description="Comfortable chinos",
            price=49.99
        )
    
    def test_product_size_creation(self):
        """Test creating product sizes"""
        size = ProductSize.objects.create(
            product=self.product,
            size="32",
            is_available=True
        )
        self.assertEqual(size.product, self.product)
        self.assertEqual(size.size, "32")
        self.assertTrue(size.is_available)


class ProductColorModelTest(TestCase):
    """Test ProductColor model"""
    
    def setUp(self):
        self.category = Category.objects.create(name="Jackets")
        self.product = Product.objects.create(
            name="Denim Jacket",
            category=self.category,
            description="Classic denim jacket",
            price=79.99
        )
    
    def test_product_color_creation(self):
        """Test creating product colors"""
        color = ProductColor.objects.create(
            product=self.product,
            color_name="Blue",
            color_code="#0000FF",
            is_available=True
        )
        self.assertEqual(color.product, self.product)
        self.assertEqual(color.color_name, "Blue")
        self.assertEqual(color.color_code, "#0000FF")


class InventoryLogModelTest(TestCase):
    """Test InventoryLog model"""
    
    def setUp(self):
        self.category = Category.objects.create(name="Accessories")
        self.product = Product.objects.create(
            name="Leather Belt",
            category=self.category,
            description="Premium leather belt",
            price=34.99
        )
        self.admin_user = User.objects.create_user(
            username="admin",
            email="admin@fabvibe.com",
            password="admin123",
            is_staff=True
        )
    
    def test_inventory_log_creation(self):
        """Test creating an inventory log entry"""
        log = InventoryLog.objects.create(
            product=self.product,
            admin=self.admin_user,
            quantity_change=50,
            reason="Initial stock"
        )
        self.assertEqual(log.product, self.product)
        self.assertEqual(log.admin, self.admin_user)
        self.assertEqual(log.quantity_change, 50)
        self.assertEqual(log.reason, "Initial stock")
        self.assertIsNotNone(log.timestamp)
    
    def test_inventory_log_negative_change(self):
        """Test logging inventory reduction"""
        log = InventoryLog.objects.create(
            product=self.product,
            admin=self.admin_user,
            quantity_change=-10,
            reason="Order fulfillment"
        )
        self.assertEqual(log.quantity_change, -10)
        self.assertEqual(log.reason, "Order fulfillment")
    
    def test_inventory_log_without_admin(self):
        """Test creating log without admin (system-generated)"""
        log = InventoryLog.objects.create(
            product=self.product,
            quantity_change=-5,
            reason="Automatic order deduction"
        )
        self.assertIsNone(log.admin)
        self.assertEqual(log.quantity_change, -5)
    
    def test_inventory_log_ordering(self):
        """Test that logs are ordered by timestamp descending"""
        import time
        log1 = InventoryLog.objects.create(
            product=self.product,
            quantity_change=100,
            reason="First entry"
        )
        time.sleep(0.01)  # Small delay to ensure different timestamps
        log2 = InventoryLog.objects.create(
            product=self.product,
            quantity_change=-20,
            reason="Second entry"
        )
        logs = InventoryLog.objects.all()
        self.assertEqual(logs[0], log2)  # Most recent first
        self.assertEqual(logs[1], log1)
