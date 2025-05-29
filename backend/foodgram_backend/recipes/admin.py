from django.contrib import admin

from .models import (
    Ingredient,
    Recipe,
    RecipeIngredient,
    Favorite,
    ShoppingCart
)


class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'author',
    )
    readonly_fields = ('favorites',)

    search_fields = ('name', 'author__username',)

    def favorites(self, recipe):
        return recipe.favorited_by.count()
    favorites.short_description = 'Число добавлений в избранное'


class IngridientAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'measurement_unit',
    )

    search_fields = ('name',)


admin.site.register(Ingredient, IngridientAdmin)
admin.site.register(Recipe, RecipeAdmin)
admin.site.register(RecipeIngredient)
admin.site.register(Favorite)
admin.site.register(ShoppingCart)
