# core/views_reference.py
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import ReferenceItem, ListItem, Receipt
from .views_common import user_household_or_404, get_or_create_open_list


@login_required
def reference_list(request, household_id: int):
    household = user_household_or_404(request.user, household_id)

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        aisle = (request.POST.get("aisle") or ReferenceItem.AISLE_GROCERY).strip()
        qty = (request.POST.get("default_quantity") or "").strip()
        note = (request.POST.get("default_note") or "").strip()

        if name:
            ReferenceItem.objects.get_or_create(
                household=household,
                name=name,
                defaults={
                    "aisle": aisle,
                    "default_quantity": qty,
                    "default_note": note,
                },
            )
        return redirect("reference_list", household_id=household.id)

    items = ReferenceItem.objects.filter(household=household).order_by("aisle", "name")
    selected_count = items.filter(is_selected=True, is_active=True).count()

    return render(
        request,
        "core/reference_list.html",
        {
            "household": household,
            "items": items,
            "selected_count": selected_count,
            "aisle_choices": ReferenceItem.AISLE_CHOICES,
        },
    )


@login_required
@require_POST
def reference_toggle_active(request, item_id: int):
    item = get_object_or_404(ReferenceItem, id=item_id)
    user_household_or_404(request.user, item.household_id)

    item.is_active = not item.is_active
    item.save(update_fields=["is_active"])
    return redirect("reference_list", household_id=item.household_id)


@login_required
@require_POST
def reference_toggle_selected(request, item_id: int):
    item = get_object_or_404(ReferenceItem, id=item_id)
    user_household_or_404(request.user, item.household_id)

    if item.is_active:
        item.is_selected = not item.is_selected
        item.save(update_fields=["is_selected"])
    return redirect("reference_list", household_id=item.household_id)


@login_required
@require_POST
def reference_clear_selected(request, household_id: int):
    household = user_household_or_404(request.user, household_id)
    ReferenceItem.objects.filter(household=household, is_selected=True).update(is_selected=False)
    return redirect("reference_list", household_id=household.id)


@login_required
@require_POST
def generate_shopping_list_from_reference(request, household_id: int):
    """
    Génère la liste de courses (session en cours) à partir du catalogue (items sélectionnés).

    Règle métier:
    - Une liste "ouverte" est une session de courses en cours.
    - Dès qu'un ticket (Receipt) existe pour une liste, cette session est terminée.
      Donc si on (re)génère depuis le catalogue, on doit partir sur une NOUVELLE liste ouverte.
    """
    household = user_household_or_404(request.user, household_id)

    with transaction.atomic():
        # 1) Liste ouverte actuelle (si aucune => créée)
        shopping_list = get_or_create_open_list(household)

        # 2) Si un ticket existe déjà sur cette liste, on clôture la session et on repart sur une nouvelle liste
        if Receipt.objects.filter(shopping_list=shopping_list).exists():
            shopping_list.closed_at = timezone.now()
            shopping_list.save(update_fields=["closed_at"])
            shopping_list = get_or_create_open_list(household)

        # 3) On remplace le contenu de la liste ouverte (session en cours)
        shopping_list.items.all().delete()

        refs = ReferenceItem.objects.filter(
            household=household,
            is_active=True,
            is_selected=True,
        ).order_by("aisle", "name")

        # 4) Re-création des items de liste
        ListItem.objects.bulk_create([
            ListItem(
                shopping_list=shopping_list,
                name=r.name,
                aisle=r.aisle,
                quantity=r.default_quantity,
                note=r.default_note,
                created_by=request.user,
            )
            for r in refs
        ])

    return redirect("shopping_list_detail", shopping_list_id=shopping_list.id)
