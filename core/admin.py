from django.contrib import admin
from .models import Household, Membership


@admin.register(Household)
class HouseholdAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_at")


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("id", "household", "user", "role", "created_at")
    list_filter = ("role",)
