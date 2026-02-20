# core/urls.py

from django.urls import path

from . import views
from . import views_reference
from . import views_shopping
from . import views_receipt


urlpatterns = [

    # ===============================
    # Accueil
    # ===============================
    path("", views_shopping.shopping_lists, name="home"),


    # ===============================
    # Foyers
    # ===============================
    path("foyers/", views.my_households, name="my_households"),
    path("foyers/creer/", views.create_household, name="create_household"),


    # ===============================
    # Listes de courses (sessions)
    # ===============================
    path("listes-de-courses/", views_shopping.shopping_lists, name="shopping_lists"),
    path("shopping-lists/", views_shopping.shopping_lists, name="shopping_lists_en"),

    path(
        "shopping-lists/<int:shopping_list_id>/",
        views_shopping.shopping_list_detail,
        name="shopping_list_detail",
    ),

    path(
        "shopping-lists/<int:shopping_list_id>/items/add/",
        views_shopping.add_list_item,
        name="add_list_item",
    ),

    path(
        "items/<int:item_id>/toggle/",
        views_shopping.toggle_list_item,
        name="toggle_list_item",
    ),

    path(
        "items/<int:item_id>/estimate/",
        views_shopping.update_estimated_price,
        name="update_estimated_price",
    ),

    path(
        "items/<int:item_id>/delete/",
        views_shopping.delete_list_item,
        name="delete_list_item",
    ),


    # ===============================
    # Catalogue (références)
    # ===============================
    path(
        "foyers/<int:household_id>/catalogue/",
        views_reference.reference_list,
        name="reference_list",
    ),

    path(
        "reference/<int:item_id>/toggle-active/",
        views_reference.reference_toggle_active,
        name="reference_toggle_active",
    ),

    path(
        "reference/<int:item_id>/toggle-selected/",
        views_reference.reference_toggle_selected,
        name="reference_toggle_selected",
    ),

    path(
        "foyers/<int:household_id>/reference/clear-selected/",
        views_reference.reference_clear_selected,
        name="reference_clear_selected",
    ),

    path(
        "foyers/<int:household_id>/reference/generate-shopping-list/",
        views_reference.generate_shopping_list_from_reference,
        name="generate_shopping_list_from_reference",
    ),


    # ===============================
    # Tickets (caisse)
    # ===============================

    # Historique
    path(
        "tickets/",
        views_receipt.receipt_list,
        name="receipt_list",
    ),

    # ✅ Purge (staff only)
    path(
        "tickets/purge/",
        views_receipt.receipt_purge_confirm,
        name="receipt_purge",
    ),

    # Création depuis une liste
    path(
        "shopping-lists/<int:shopping_list_id>/ticket/create/",
        views_receipt.create_receipt,
        name="create_receipt",
    ),

    # Détail ticket
    path(
        "tickets/<int:receipt_id>/",
        views_receipt.receipt_detail,
        name="receipt_detail",
    ),

    # Mise à jour en-tête ticket
    path(
        "tickets/<int:receipt_id>/update/",
        views_receipt.update_receipt_header,
        name="update_receipt_header",
    ),

    # Mise à jour prix ligne ticket
    path(
        "ticket-items/<int:item_id>/price/",
        views_receipt.update_receipt_item_price,
        name="update_receipt_item_price",
    ),

    # Validation / contrôle ticket
    path(
        "tickets/<int:receipt_id>/validate/",
        views_receipt.validate_receipt,
        name="validate_receipt",
    ),
]
