from django.contrib import admin
from core.models import (
    Household,
    Membership,
    ReferenceItem,
    ShoppingList,
    ListItem,
    Receipt,
    ReceiptItem,
)


@admin.register(Household)
class HouseholdAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_by", "created_at")
    search_fields = ("name",)
    list_select_related = ("created_by",)
    ordering = ("name",)


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("id", "household", "user", "role", "created_at")
    list_filter = ("role",)
    search_fields = ("household__name", "user__username", "user__email")
    list_select_related = ("household", "user")
    ordering = ("household__name", "user__username")


@admin.register(ReferenceItem)
class ReferenceItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "household",
        "name",
        "aisle",
        "default_qty_value",
        "default_unit",
        "is_active",
        "is_selected",
        "created_at",
    )
    list_filter = ("aisle", "default_unit", "is_active", "is_selected")
    search_fields = ("name", "household__name")
    list_select_related = ("household",)
    ordering = ("household__name", "aisle", "name")


@admin.register(ShoppingList)
class ShoppingListAdmin(admin.ModelAdmin):
    list_display = ("id", "household", "name", "created_at")
    search_fields = ("household__name", "name")
    list_select_related = ("household",)
    ordering = ("household__name",)


@admin.register(ListItem)
class ListItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "shopping_list",
        "name",
        "aisle",
        "is_checked",
        "qty_value",
        "unit",
        "estimated_price",
        "created_by",
        "created_at",
    )
    list_filter = ("aisle", "unit", "is_checked")
    search_fields = ("name", "shopping_list__household__name")
    list_select_related = ("shopping_list", "created_by")
    ordering = ("-created_at",)


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "household",
        "shopping_list",
        "store_name",
        "purchased_at",
        "paper_total",
        "created_at",
    )
    list_filter = ("purchased_at",)
    search_fields = ("household__name", "store_name")
    list_select_related = ("household", "shopping_list")
    ordering = ("-purchased_at",)


@admin.register(ReceiptItem)
class ReceiptItemAdmin(admin.ModelAdmin):
    list_display = ("id", "receipt", "position", "name", "estimated_price", "actual_price", "list_item", "created_at")
    search_fields = ("name", "receipt__household__name")
    list_select_related = ("receipt", "list_item")
    ordering = ("receipt_id", "position", "id")