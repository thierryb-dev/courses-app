from rest_framework.permissions import BasePermission


class IsHouseholdMember(BasePermission):
    """
    Autorise l'accès si l'utilisateur est membre du household lié à l'objet.
    Supporte Household, ShoppingList, ListItem.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        # Household direct
        if obj.__class__.__name__ == "Household":
            return obj.memberships.filter(user=user).exists()

        # ShoppingList -> household
        if hasattr(obj, "household"):
            return obj.household.memberships.filter(user=user).exists()

        # ListItem -> shopping_list -> household
        if hasattr(obj, "shopping_list"):
            return obj.shopping_list.household.memberships.filter(user=user).exists()

        return False
