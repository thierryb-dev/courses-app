from django.urls import path

from core.views import my_households, create_household
from core.views_shopping import (
    shopping_lists,
    create_shopping_list,
    shopping_list_detail,
    add_list_item,
    toggle_list_item,
    delete_list_item,
    clear_checked_items,
)
from core.views_reference import (
    reference_list,
    reference_toggle_active,
    generate_shopping_list_from_reference,
)

urlpatterns = [
    # Home => Mes foyers
    path("", my_households, name="home"),

    # Households
    path("households/", my_households, name="my_households"),
    path("households/create/", create_household, name="create_household"),

    # Catalogue / référence
    path("households/<int:household_id>/reference/", reference_list, name="reference_list"),
    path("reference-items/<int:item_id>/toggle-active/", reference_toggle_active, name="reference_toggle_active"),
    path("households/<int:household_id>/reference/generate/", generate_shopping_list_from_reference, name="generate_from_reference"),

    # Shopping lists
    path("shopping-lists/", shopping_lists, name="shopping_lists"),
    path("shopping-lists/create/<int:household_id>/", create_shopping_list, name="create_shopping_list"),
    path("shopping-lists/<int:list_id>/", shopping_list_detail, name="shopping_list_detail"),
    path("shopping-lists/<int:list_id>/clear-checked/", clear_checked_items, name="clear_checked_items"),

    # Items
    path("shopping-lists/<int:list_id>/items/add/", add_list_item, name="add_list_item"),
    path("list-items/<int:item_id>/toggle/", toggle_list_item, name="toggle_list_item"),
    path("list-items/<int:item_id>/delete/", delete_list_item, name="delete_list_item"),
]
