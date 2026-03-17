from .models import Category


def categories(request):
    """
    Context processor to add categories and subcategories to all templates
    """
    # Get all parent categories (categories without a parent)
    parent_categories = Category.objects.filter(parent__isnull=True, is_active=True).prefetch_related('subcategories')
    
    return {'categories': parent_categories}
