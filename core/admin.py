from django.contrib import admin
from .models import Household, Membership, ShoppingList, ListItem


@admin.register(Household)
class HouseholdAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_by", "created_at")
    search_fields = ("name",)


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("id", "household", "user", "role", "joined_at")
    list_filter = ("role", "household")
    search_fields = ("user__username", "user__email", "household__name")


@admin.register(ShoppingList)
class ShoppingListAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "household", "created_by", "created_at")
    search_fields = ("name",)
    list_filter = ("household",)


@admin.register(ListItem)
class ListItemAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "shopping_list", "is_checked", "created_by", "created_at")
    list_filter = ("is_checked", "shopping_list")
    search_fields = ("name", "note", "shopping_list__name")
