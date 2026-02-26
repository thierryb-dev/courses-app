from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import ReferenceItem, ListItem, Receipt, UNIT_CHOICES, UNIT_UNIT
from .views_common import user_household_or_404, get_or_create_open_list


def _parse_decimal_or_none(raw: str) -> Decimal | None:
    raw = (raw or "").strip().replace(",", ".")
    if raw == "":
        return None
    return Decimal(raw)


def _normalize_qty_unit(qty: Decimal | None, unit: str) -> tuple[Decimal | None, str]:
    unit = (unit or UNIT_UNIT).strip() or UNIT_UNIT
    if qty is None:
        return (Decimal("1") if unit else None), unit
    return qty, unit


def _normalize_aisle(raw: str | None) -> str:
    raw = (raw or "").strip()
    aisle_map = dict(ReferenceItem.AISLE_CHOICES)
    if raw in aisle_map:
        return raw
    return ReferenceItem.AISLE_CHOICES[0][0]


def _group_by_aisle(items) -> list[dict[str, Any]]:
    """
    Regroupe des ReferenceItem déjà triés par aisle.
    Retourne une liste de groupes:
      [
        {
          "aisle": "al_fruits_veg",
          "label": "Alimentaire ▸ Fruits & légumes frais",
          "items": [ReferenceItem, ...]
        },
        ...
      ]
    """
    aisle_label_map = dict(ReferenceItem.AISLE_CHOICES)

    grouped: list[dict[str, Any]] = []
    current_aisle: str | None = None
    current_bucket: list[ReferenceItem] = []

    def _flush():
        nonlocal current_aisle, current_bucket
        if current_aisle is None:
            return
        grouped.append(
            {
                "aisle": current_aisle,
                "label": aisle_label_map.get(current_aisle, current_aisle),
                "items": current_bucket,
            }
        )
        current_aisle = None
        current_bucket = []

    for it in items:
        if current_aisle is None:
            current_aisle = it.aisle
            current_bucket = [it]
            continue

        if it.aisle != current_aisle:
            _flush()
            current_aisle = it.aisle
            current_bucket = [it]
        else:
            current_bucket.append(it)

    _flush()
    return grouped


@login_required
def reference_list(request, household_id: int):
    household = user_household_or_404(request.user, household_id)

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        aisle = _normalize_aisle(request.POST.get("aisle"))

        qty_raw = request.POST.get("default_qty_value") or ""
        unit = (request.POST.get("default_unit") or UNIT_UNIT).strip()
        note = (request.POST.get("default_note") or "").strip()

        price_raw = request.POST.get("default_unit_price") or ""

        default_qty_value = None
        default_unit_price = None

        try:
            default_qty_value = _parse_decimal_or_none(qty_raw)
        except (InvalidOperation, ValueError):
            default_qty_value = None

        try:
            default_unit_price = _parse_decimal_or_none(price_raw)
        except (InvalidOperation, ValueError):
            default_unit_price = None

        default_qty_value, unit = _normalize_qty_unit(default_qty_value, unit)

        if name:
            ReferenceItem.objects.get_or_create(
                household=household,
                name=name,
                defaults={
                    "aisle": aisle,
                    "default_qty_value": default_qty_value,
                    "default_unit": unit,
                    "default_note": note,
                    "default_unit_price": default_unit_price,
                },
            )

        return redirect("reference_list", household_id=household.id)

    # ⚙️ Base queryset: tri pour groupement stable par rayon
    items = ReferenceItem.objects.filter(household=household).order_by("is_active", "aisle", "name")

    active_count = items.filter(is_active=True).count()
    selected_count = items.filter(is_selected=True, is_active=True).count()

    # ✅ Groupes prêts à afficher (par rayon)
    active_items = items.filter(is_active=True).order_by("aisle", "name")
    archived_items = items.filter(is_active=False).order_by("aisle", "name")

    grouped_active = _group_by_aisle(active_items)
    grouped_archived = _group_by_aisle(archived_items)

    return render(
        request,
        "core/reference_list.html",
        {
            "household": household,
            # Compat: si ton template utilise encore "items"
            "items": items,
            "active_count": active_count,
            "selected_count": selected_count,
            "aisle_choices": ReferenceItem.AISLE_CHOICES,
            "unit_choices": UNIT_CHOICES,
            # ✅ Nouveaux contextes pour affichage par rayon
            "grouped_active": grouped_active,
            "grouped_archived": grouped_archived,
        },
    )


@login_required
@require_POST
def reference_toggle_active(request, item_id: int):
    item = get_object_or_404(ReferenceItem, id=item_id)
    user_household_or_404(request.user, item.household_id)

    item.is_active = not item.is_active
    if not item.is_active and item.is_selected:
        item.is_selected = False
        item.save(update_fields=["is_active", "is_selected"])
    else:
        item.save(update_fields=["is_active"])

    return redirect("reference_list", household_id=item.household_id)


@login_required
@require_POST
def reference_toggle_selected(request, item_id: int):
    item = get_object_or_404(ReferenceItem, id=item_id)
    user_household_or_404(request.user, item.household_id)

    if not item.is_active:
        messages.error(request, "Produit archivé : réactive-le pour pouvoir l’ajouter à la liste.")
        return redirect("reference_list", household_id=item.household_id)

    item.is_selected = not item.is_selected
    item.save(update_fields=["is_selected"])
    return redirect("reference_list", household_id=item.household_id)


@login_required
@require_POST
def reference_update_details(request, item_id: int):
    item = get_object_or_404(ReferenceItem, id=item_id)
    user_household_or_404(request.user, item.household_id)

    qty_raw = request.POST.get("default_qty_value") or ""
    unit = (request.POST.get("default_unit") or UNIT_UNIT).strip()
    note = (request.POST.get("default_note") or "").strip()
    aisle = _normalize_aisle(request.POST.get("aisle"))
    price_raw = request.POST.get("default_unit_price") or ""

    qty = None
    unit_price = None

    try:
        qty = _parse_decimal_or_none(qty_raw)
    except (InvalidOperation, ValueError):
        qty = None

    try:
        unit_price = _parse_decimal_or_none(price_raw)
    except (InvalidOperation, ValueError):
        unit_price = None

    qty, unit = _normalize_qty_unit(qty, unit)

    item.default_qty_value = qty
    item.default_unit = unit
    item.default_note = note
    item.aisle = aisle
    item.default_unit_price = unit_price

    item.save(update_fields=["default_qty_value", "default_unit", "default_note", "aisle", "default_unit_price"])
    messages.success(request, "Produit mis à jour.")
    return redirect("reference_list", household_id=item.household_id)


@login_required
@require_POST
def reference_delete(request, item_id: int):
    item = get_object_or_404(ReferenceItem, id=item_id)
    user_household_or_404(request.user, item.household_id)

    household_id = item.household_id
    name = item.name
    item.delete()

    messages.success(request, f"Produit supprimé : {name}")
    return redirect("reference_list", household_id=household_id)


@login_required
@require_POST
def reference_clear_selected(request, household_id: int):
    household = user_household_or_404(request.user, household_id)
    ReferenceItem.objects.filter(household=household, is_selected=True).update(is_selected=False)
    messages.success(request, "Sélection vidée.")
    return redirect("reference_list", household_id=household.id)


@login_required
@require_POST
def generate_shopping_list_from_reference(request, household_id: int):
    """
    Génère la liste magasin à partir des produits “À acheter”.
    ✅ Copie: rayon + qté + unité + note + prix unitaire
    ✅ Calcule estimated_price = qté × prix_unitaire
    """
    household = user_household_or_404(request.user, household_id)

    with transaction.atomic():
        shopping_list = get_or_create_open_list(household)

        # Si un ticket existe déjà pour cette liste ouverte, on clôture et on en recrée une
        if Receipt.objects.filter(shopping_list=shopping_list).exists():
            shopping_list.closed_at = timezone.now()
            shopping_list.save(update_fields=["closed_at"])
            shopping_list = get_or_create_open_list(household)

        # Reset items
        shopping_list.items.all().delete()

        refs = ReferenceItem.objects.filter(
            household=household,
            is_active=True,
            is_selected=True,
        ).order_by("aisle", "name")

        items_to_create: list[ListItem] = []
        for r in refs:
            li = ListItem(
                shopping_list=shopping_list,
                name=r.name,
                aisle=r.aisle,
                qty_value=r.default_qty_value,
                unit=r.default_unit,
                note=r.default_note,
                unit_price=r.default_unit_price,
                created_by=request.user,
            )
            li.recompute_estimated_price()
            items_to_create.append(li)

        ListItem.objects.bulk_create(items_to_create)

    messages.success(request, "Liste générée (qté + prix unitaire copiés du catalogue).")
    return redirect("shopping_list_detail", shopping_list_id=shopping_list.id)