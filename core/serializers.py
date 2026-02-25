from rest_framework import serializers
from .models import Household, Membership, ShoppingList, ListItem, ReferenceItem


class HouseholdSerializer(serializers.ModelSerializer):
    class Meta:
        model = Household
        fields = ["id", "name", "created_by", "created_at"]
        read_only_fields = ["created_by", "created_at"]


class MembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Membership
        fields = ["id", "household", "user", "role", "created_at"]
        read_only_fields = ["created_at"]


class ReferenceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferenceItem
        fields = [
            "id",
            "household",
            "name",
            "aisle",
            "default_qty_value",
            "default_unit",
            "default_note",
            "is_active",
            "is_selected",
            "created_at",
        ]
        read_only_fields = ["created_at"]


class ListItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListItem
        fields = [
            "id",
            "shopping_list",
            "name",
            "aisle",
            "qty_value",
            "unit",
            "note",
            "is_checked",
            "checked_at",
            "checked_by",
            "estimated_price",
            "created_by",
            "created_at",
        ]
        read_only_fields = ["checked_at", "checked_by", "created_by", "created_at"]


class ShoppingListSerializer(serializers.ModelSerializer):
    items = ListItemSerializer(many=True, read_only=True)

    class Meta:
        model = ShoppingList
        fields = ["id", "household", "name", "created_at", "items"]
        read_only_fields = ["created_at"]