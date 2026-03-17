from django.test import TestCase, RequestFactory
from .models import Category
from .context_processors import categories


class CategoriesContextProcessorTest(TestCase):
    """Test categories context processor"""
    
    def setUp(self):
        """Set up test data"""
        self.factory = RequestFactory()
        
        # Create parent categories
        self.men_category = Category.objects.create(
            name='Men',
            slug='men',
            is_active=True
        )
        
        self.women_category = Category.objects.create(
            name='Women',
            slug='women',
            is_active=True
        )
        
        # Create subcategories
        self.men_shirts = Category.objects.create(
            name='Shirts',
            slug='men-shirts',
            parent=self.men_category,
            is_active=True
        )
        
        self.men_pants = Category.objects.create(
            name='Pants',
            slug='men-pants',
            parent=self.men_category,
            is_active=True
        )
        
        self.women_dresses = Category.objects.create(
            name='Dresses',
            slug='women-dresses',
            parent=self.women_category,
            is_active=True
        )
        
        # Create inactive category (should not appear)
        self.inactive_category = Category.objects.create(
            name='Inactive',
            slug='inactive',
            is_active=False
        )
    
    def test_context_processor_returns_categories(self):
        """Test that context processor returns categories"""
        request = self.factory.get('/')
        context = categories(request)
        
        self.assertIn('categories', context)
        self.assertIsNotNone(context['categories'])
    
    def test_context_processor_returns_only_parent_categories(self):
        """Test that context processor returns only parent categories"""
        request = self.factory.get('/')
        context = categories(request)
        
        parent_categories = list(context['categories'])
        
        # Should return 2 parent categories (Men and Women)
        self.assertEqual(len(parent_categories), 2)
        
        # Verify they are parent categories
        category_names = [cat.name for cat in parent_categories]
        self.assertIn('Men', category_names)
        self.assertIn('Women', category_names)
    
    def test_context_processor_excludes_inactive_categories(self):
        """Test that inactive categories are not included"""
        request = self.factory.get('/')
        context = categories(request)
        
        parent_categories = list(context['categories'])
        category_names = [cat.name for cat in parent_categories]
        
        # Inactive category should not be in the list
        self.assertNotIn('Inactive', category_names)
    
    def test_context_processor_includes_subcategories(self):
        """Test that subcategories are accessible through parent categories"""
        request = self.factory.get('/')
        context = categories(request)
        
        parent_categories = list(context['categories'])
        
        # Find Men category
        men_cat = next(cat for cat in parent_categories if cat.name == 'Men')
        
        # Check subcategories are accessible
        subcategories = list(men_cat.subcategories.all())
        self.assertEqual(len(subcategories), 2)
        
        subcategory_names = [sub.name for sub in subcategories]
        self.assertIn('Shirts', subcategory_names)
        self.assertIn('Pants', subcategory_names)
    
    def test_categories_available_in_template_context(self):
        """Test that categories are available in rendered templates"""
        response = self.client.get('/')
        
        # Categories should be in context for any page
        self.assertIn('categories', response.context)
        
        categories_list = list(response.context['categories'])
        self.assertEqual(len(categories_list), 2)
