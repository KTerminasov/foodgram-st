from django.contrib.auth import get_user_model
from django.conf import settings
from django.shortcuts import render
from djoser.views import UserViewSet
from rest_framework import status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import Subscription
from recipes.models import (
    Ingredient,
    Recipe
)

from .pagination import CustomPagination
from .permissions import IsOwnerOrReadOnly
from .serializers import (
    AvatarSerializer,
    CreateUpdateRecipeSerializer,
    SetPasswordSerializer,
    IngredientSerializer,
    ReadDeleteRecipeSerializer,
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
        methods=['get'],
        permission_classes=[IsAuthenticated]
    )
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(
        detail=False,
        methods=['put', 'delete'],
        permission_classes=[IsAuthenticated],
        url_path='me/avatar'
    )
    def avatar(self, request):
        if request.method == 'PUT':
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
        methods=['post'],
        permission_classes=[IsAuthenticated]
    )
    def set_password(self, request):
        serializer = SetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            if not request.user.check_password(
                serializer.validated_data['current_password']
            ):
                return Response(
                    {'current_password': 'Неверный пароль'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            request.user.set_password(
                serializer.validated_data['new_password'])
            request.user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class IngridientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = ReadDeleteRecipeSerializer
    pagination_class = CustomPagination
    permission_classes = (IsOwnerOrReadOnly, )

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return CreateUpdateRecipeSerializer
        return ReadDeleteRecipeSerializer

    @action(detail=True, methods=('GET',), url_path='get-link',)
    def get_link(self, request, **kwargs):
        link = (
            f'{settings.ALLOWED_HOSTS[0]}/s/'
            f'{self.get_object().create_short_link()}'
        )
        return Response({'short-link': link}, status=status.HTTP_200_OK)
