from django.contrib.auth import get_user_model
from django.conf import settings
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import status, viewsets, filters
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
)
from users.models import Subscription

from .filters import IngredientFilter, RecipeFilter
from .pagination import CustomPagination
from .permissions import IsOwnerOrReadOnly
from .serializers import (
    AvatarSerializer,
    CreateUpdateRecipeSerializer,
    SetPasswordSerializer,
    SubscriptionSerializer,
    IngredientSerializer,
    MinifiedRecipeSerializer,
    ReadRecipeSerializer,
    UserSerializer
)

User = get_user_model()


class CustomUserViewSet(UserViewSet):

    serializer_class = UserSerializer
    pagination_class = CustomPagination

    def get_queryset(self):
        return User.objects.all()

    @action(
        detail=False,
        methods=('GET',),
        permission_classes=(IsAuthenticated,)
    )
    def me(self, request):
        """Информация о пользователе, сделавшем запрос."""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    @action(
        detail=False,
        methods=('PUT', 'DELETE',),
        permission_classes=(IsAuthenticated,),
        url_path='me/avatar'
    )
    def avatar(self, request):
        """Добавление и удаление аватара."""
        if request.method == 'PUT':

            if 'avatar' not in request.data:
                return Response(
                    {'avatar': 'Обязательное поле.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            serializer = AvatarSerializer(
                request.user, data=request.data, partial=True
            )

            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)

            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )

        elif request.method == 'DELETE':

            request.user.avatar.delete()
            request.user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=('POST',),
        permission_classes=(IsAuthenticated,)
    )
    def set_password(self, request):
        """Установка пароля."""
        serializer = SetPasswordSerializer(data=request.data)

        if serializer.is_valid():

            if not request.user.check_password(
                serializer.validated_data['current_password']
            ):
                return Response(
                    {'current_password': 'Неверный пароль'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            request.user.set_password(serializer.validated_data['new_password'])
            request.user.save()

            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class IngridientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (AllowAny,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = ReadRecipeSerializer
    pagination_class = CustomPagination
    permission_classes = (IsOwnerOrReadOnly, )
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        """Назначение сериализатора в зависимости от действия."""
        if self.action in ('create', 'update', 'partial_update'):
            return CreateUpdateRecipeSerializer

        return ReadRecipeSerializer

    @action(
        detail=True,
        methods=('GET',),
        url_path='get-link',
    )
    def get_link(self, request, **kwargs):
        """Получение короткой ссылки на рецепт."""
        link = (
            f'{settings.ALLOWED_HOSTS[0]}/s/'
            f'{self.get_object().create_short_link()}'
        )

        return Response({'short-link': link}, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=('POST', 'DELETE',),
        permission_classes=(IsAuthenticated,)
    )
    def shopping_cart(self, request, pk=None):
        """Создание списка покупок."""
        recipe = self.get_object()

        if request.method == 'POST':

            if ShoppingCart.objects.filter(
                user=request.user,
                recipe=recipe
            ).exists():
                return Response(
                    {'errors': 'Рецепт уже в списке покупок'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            ShoppingCart.objects.create(user=request.user, recipe=recipe)
            serializer = MinifiedRecipeSerializer(recipe)

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        shopping_cart = ShoppingCart.objects.filter(
            user=request.user, recipe=recipe
        )
        if not shopping_cart.exists():
            return Response(
                {'errors': 'Рецепта нет в списке покупок'},
                status=status.HTTP_400_BAD_REQUEST
            )
        shopping_cart.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        """Преобразование списка покупок в текстовый файл."""
        ingredients = RecipeIngredient.objects.filter(
            recipe__added_in_shopping_cart_by__user=request.user
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(total_amount=Sum('amount'))

        shopping_list = []
        for ingredient in ingredients:
            shopping_list.append(
                f"{ingredient['ingredient__name']} - "
                f"{ingredient['total_amount']} "
                f"{ingredient['ingredient__measurement_unit']}"
            )

        response = HttpResponse('\n'.join(shopping_list),
                                content_type='text/plain')
        response['Content-Disposition'] = (
            'attachment; filename="shopping_list.txt"'
        )

        return response

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=(IsAuthenticated,)
    )
    def favorite(self, request, pk=None):
        """Добавление/удаление рецепта в избранное."""
        recipe = self.get_object()
        if request.method == 'POST':

            if Favorite.objects.filter(
                user=request.user, recipe=recipe
            ).exists():
                return Response(
                    {'errors': 'Рецепт уже в избранном'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            Favorite.objects.create(user=request.user, recipe=recipe)
            serializer = MinifiedRecipeSerializer(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        favorite = Favorite.objects.filter(user=request.user, recipe=recipe)
        if not favorite.exists():
            return Response(
                {'errors': 'Рецепта нет в избранном'},
                status=status.HTTP_400_BAD_REQUEST
            )
        favorite.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class SubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = SubscriptionSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = CustomPagination

    def get_queryset(self):
        return Subscription.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        """Подписка пользователя на другого."""
        following = get_object_or_404(User, id=kwargs.get('id'))

        if following == request.user:
            return Response(
                {'errors': 'Нельзя подписаться на самого себя'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if Subscription.objects.filter(
            user=request.user, following=following
        ).exists():
            return Response(
                {'errors': 'Вы уже подписаны на этого пользователя'},
                status=status.HTTP_400_BAD_REQUEST
            )

        subscription = Subscription.objects.create(
            user=request.user, following=following
        )
        serializer = self.get_serializer(subscription)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        """Отписка пользователя от другого."""
        following = get_object_or_404(User, id=kwargs.get('id'))
        subscription = Subscription.objects.filter(
            user=request.user, following=following
        )

        if not subscription.exists():
            return Response(
                {'errors': 'Вы не подписаны на этого пользователя'},
                status=status.HTTP_400_BAD_REQUEST
            )
        subscription.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
