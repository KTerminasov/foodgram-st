from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    "Пользователь может редактировать объект, только если он его автор."

    def has_permission(self, request, view):
        return (
            request.method in permissions.SAFE_METHODS
            or request.user.is_authenticated
        )

    def has_object_permission(self, request, view, obj):
        return (
            obj.author == request.user
            or request.method in permissions.SAFE_METHODS
        )
