from django.shortcuts import render
from common.nutrition_score import NutritionalScore
from foods.models import Food

def search_page(request):
    
    foods = list(Food.objects.all())
    
    foods_sorted = sorted(
        foods,
        key=lambda food: NutritionalScore(food),
        reverse=True
    )

    context = {foods_sorted}

    return render(request, "search_page.html", context)