import base64

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from rest_framework import serializers

from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
)
from users.models import Subscription

User = get_user_model()


class Base64ImageField(serializers.ImageField):
    """Преобразование из формата base64 в изображение."""

    def to_internal_value(self, data):

        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
        return super().to_internal_value(data)


class AvatarSerializer(serializers.ModelSerializer):
    """Используется для PUT-запроса для добавления аватара."""

    avatar = Base64ImageField()

    class Meta:
        model = User
        fields = ('avatar', )


class UserSerializer(serializers.ModelSerializer):
    """Используется для POST- и GET- запросов при работе с пользователями."""

    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'avatar',
        )

    def get_is_subscribed(self, following):
        request = self.context.get('request')

        if request and request.user.is_authenticated:
            return request.user.followers.filter(following=following).exists()
        return False


class SetPasswordSerializer(serializers.Serializer):
    """Используется для POST-запроса, задающего пароль."""

    new_password = serializers.CharField(required=True)
    current_password = serializers.CharField(required=True)


class IngredientSerializer(serializers.ModelSerializer):
    """Используется для GET-запросов при работе с ингридиентами."""

    class Meta:
        model = Ingredient
        fields = (
            'id',
            'name',
            'measurement_unit'
        )


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Используется для GET-запросов при работе с рецептами."""

    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = (
            'id',
            'name',
            'measurement_unit',
            'amount',
        )


class ReadRecipeSerializer(serializers.ModelSerializer):
    """Используется для GET-запросов при работе с рецептами."""

    author = UserSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(
        many=True,
        source='recipe_ingredients'
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time',
        )

    def get_is_favorited(self, recipe):
        """Проверка наличия рецепта в избранных."""
        request = self.context.get('request')

        if request and request.user.is_authenticated:
            return request.user.favorites.filter(recipe=recipe).exists()
        return False

    def get_is_in_shopping_cart(self, recipe):
        """Проверка наличия рецепта в корзине."""
        request = self.context.get('request')

        if request and request.user.is_authenticated:
            return request.user.shopping_cart.filter(recipe=recipe).exists()
        return False


class WriteRecipeIngredient(serializers.ModelSerializer):
    """Используется для создания списка ингредиентов в
    CreateUpdateRecipeSerializer.
    """

    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())

    class Meta:
        model = RecipeIngredient
        fields = (
            'id',
            'amount'
        )


class CreateUpdateRecipeSerializer(serializers.ModelSerializer):
    """Используется при POST- и PATCH- запросах при работе с рецептами."""
    ingredients = WriteRecipeIngredient(many=True)
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'ingredients',
            'image',
            'name',
            'text',
            'cooking_time'
        )

    def validate_ingredients(self, value):
        """Проверка корректности указания ингридиентов."""
        if not value:
            raise serializers.ValidationError(
                'Необходимо указать ингредиенты.'
            )

        ingredients_ids = [ingredient['id'] for ingredient in value]

        if len(ingredients_ids) != len(set(ingredients_ids)):
            raise serializers.ValidationError(
                'Ингредиенты в списке должны быть уникальны.'
            )

        return super().validate(value)

    def create(self, validated_data):
        """Создание рецепта с добавлением в него ингридиентов."""
        ingredients = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(
            author=self.context['request'].user,
            **validated_data
        )

        RecipeIngredient.objects.bulk_create([
            RecipeIngredient(
                recipe=recipe,
                ingredient=ingredient['id'],
                amount=ingredient['amount']
            ) for ingredient in ingredients
        ])

        return recipe

    def update(self, instance, validated_data):
        """Изменение рецепта и его ингридиентов."""

        if 'ingredients' not in validated_data:
            raise serializers.ValidationError(
                {'ingredients': 'Необходимо указать ингредиенты'}
            )

        if not validated_data['ingredients']:
            raise serializers.ValidationError(
                {'ingredients': 'Список ингредиентов не может быть пустым'}
            )

        ingredients = validated_data.pop('ingredients')
        instance = super().update(instance, validated_data)
        instance.recipe_ingredients.all().delete()

        RecipeIngredient.objects.bulk_create([
            RecipeIngredient(
                recipe=instance,
                ingredient=ingredient['id'],
                amount=ingredient['amount']
            ) for ingredient in ingredients
        ])

        return instance

    def to_representation(self, instance):
        """Использование ReadRecipeSerializer для представления данных."""
        return ReadRecipeSerializer(context=self.context).to_representation(
            instance=instance)


class MinifiedRecipeSerializer(serializers.ModelSerializer):
    """Используется для обработки GET- и POST- запросов к избранным
     и списку покупок.
     """

    class Meta:
        model = Recipe
        fields = (
            'id',
            'name',
            'image',
            'cooking_time',
        )


class SubscriptionSerializer(UserSerializer):
    """Используется для GET- и POST- запросов при работе с подписками."""

    email = serializers.EmailField(source='following.email')
    id = serializers.IntegerField(source='following.id')
    username = serializers.CharField(source='following.username')
    first_name = serializers.CharField(source='following.first_name')
    last_name = serializers.CharField(source='following.last_name')
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()
    avatar = serializers.ImageField(source='following.avatar', required=False)

    class Meta:
        model = Subscription
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count',
            'avatar'
        )

    def get_is_subscribed(self, obj):
        """Возрвращает True, так как мы уже в подписках."""
        return True

    def get_recipes(self, obj):
        """Получение списка рецептов пользователя."""
        request = self.context.get('request')
        recipes_limit = request.query_params.get('recipes_limit')
        queryset = obj.following.recipes.all()

        if recipes_limit and recipes_limit.isdigit():
            queryset = queryset[:int(recipes_limit)]

        return MinifiedRecipeSerializer(queryset, many=True).data

    def get_recipes_count(self, obj):
        """Подсчет количества рецептов."""
        return obj.following.recipes.count()
