import hashlib
from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from constants import RecipeConstants


User = get_user_model()


class Ingredient(models.Model):
    """Инридиент."""

    name = models.CharField(
        max_length=128,
        verbose_name='Название'
    )
    measurement_unit = models.CharField(
        max_length=64,
        verbose_name='Единица измерения'
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        ordering = ('name',)

    def __str__(self):
        return f'{self.name}, {self.measurement_unit}'


class Recipe(models.Model):
    """Рецепт."""

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes'
    )
    name = models.CharField(max_length=256)
    image = models.ImageField(upload_to='recipes/images/')
    text = models.TextField()
    cooking_time = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(RecipeConstants.MIN_COOKING_TIME),
            MaxValueValidator(RecipeConstants.MAX_COOKING_TIME)
        ]
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        related_name='recipes'
    )
    pub_date = models.DateTimeField(auto_now_add=True)
    short_link = short_link = models.CharField(
        max_length=10,
        unique=True,
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ('-pub_date', 'name')

    def __str__(self):
        return self.name

    def create_short_link(self):
        """Создание короткой ссылки с помощью хеширования id и name."""
        base_str = f"{self.id}{self.name}"
        hash_object = hashlib.md5(base_str.encode())
        hex_dig = hash_object.hexdigest()

        self.short_link = hex_dig[:8]
        self.save()
        return self.short_link


class RecipeIngredient(models.Model):
    """Инридиент для рецепта."""

    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='recipe_ingredients'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='recipe_ingredients'
    )
    amount = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(RecipeConstants.MIN_INGREDIENT_AMOUNT),
            MaxValueValidator(RecipeConstants.MAX_INGREDIENT_AMOUNT)
        ]
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'ingredient'],
                name='unique_ingredient_in_recipe'
            )
        ]
        verbose_name = 'Ингредиент в рецепте'
        verbose_name_plural = 'Ингредиенты в рецептах'
        ordering = (
            '-recipe__pub_date',
            'recipe__name',
            'ingredient__name',
        )

    def __str__(self):
        return f'{self.ingredient} в {self.recipe}'


class Favorite(models.Model):
    """Избранное."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorites'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='favorited_by'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_favorite'
            )
        ]
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранные'
        ordering = (
            'user__username',
            '-recipe__pub_date',
        )

    def __str__(self):
        return f'{self.recipe} в избранном у {self.user}'


class ShoppingCart(models.Model):
    """Список покупок."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='shopping_cart'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='added_in_shopping_cart_by'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_shopping_cart'
            )
        ]
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Списки покупок'
        ordering = (
            'user__username',
            '-recipe__pub_date',
        )

    def __str__(self):
        return f'{self.recipe} в списке покупок у {self.user}'
