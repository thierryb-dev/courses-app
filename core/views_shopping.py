from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import (
    Household,
    ListItem,
    Membership,
    ShoppingList,
    ReferenceItem,
    Receipt,
    UNIT_CHOICES,
    UNIT_UNIT,
)
from .views_common import get_or_create_open_list


def _user_list_or_404(user, shopping_list_id: int) -> ShoppingList:
    sl = get_object_or_404(ShoppingList, id=shopping_list_id)
    if not Membership.objects.filter(user=user, household=sl.household).exists():
        raise Http404("ShoppingList not found")
    return sl


def _user_item_or_404(user, item_id: int) -> ListItem:
    item = get_object_or_404(ListItem, id=item_id)
    if not Membership.objects.filter(user=user, household=item.shopping_list.household).exists():
        raise Http404("Item not found")
    return item


def _reject_if_closed(request: HttpRequest, shopping_list: ShoppingList) -> bool:
    if shopping_list.closed_at is not None:
        messages.error(request, "Cette liste est clôturée : aucune modification n'est autorisée.")
        return True
    return False


def _next_checked_missing_estimate(shopping_list: ShoppingList, exclude_id: int | None = None) -> ListItem | None:
    qs = shopping_list.items.filter(is_checked=True, estimated_price__isnull=True)
    if exclude_id is not None:
        qs = qs.exclude(id=exclude_id)
    return qs.order_by("aisle", "created_at", "id").first()


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


@login_required
def shopping_lists(request: HttpRequest) -> HttpResponse:
    households = Household.objects.filter(memberships__user=request.user).distinct().order_by("name")
    open_lists = [get_or_create_open_list(h) for h in households]
    return render(request, "core/shopping_lists.html", {"lists": open_lists})


@login_required
def shopping_list_detail(request: HttpRequest, shopping_list_id: int) -> HttpResponse:
    shopping_list = _user_list_or_404(request.user, shopping_list_id)
    items = shopping_list.items.all().order_by("is_checked", "aisle", "created_at", "id")

    running_total = Decimal("0.00")
    checked_count = 0
    missing_estimate_count = 0

    for it in items:
        if it.is_checked:
            checked_count += 1
            if it.estimated_price is None:
                missing_estimate_count += 1
            else:
                running_total += it.estimated_price

    has_checked = checked_count > 0

    try:
        receipt = shopping_list.receipt
    except Receipt.DoesNotExist:
        receipt = None

    is_closed = shopping_list.closed_at is not None

    focus_price = (request.GET.get("focus_price") or "").strip()
    focus_price_id = int(focus_price) if focus_price.isdigit() else None
    if focus_price_id is None:
        nxt = _next_checked_missing_estimate(shopping_list)
        focus_price_id = nxt.id if nxt else None

    return render(
        request,
        "core/shopping_list_detail.html",
        {
            "shopping_list": shopping_list,
            "items": items,
            "running_total": running_total,
            "aisle_choices": ReferenceItem.AISLE_CHOICES,
            "unit_choices": UNIT_CHOICES,
            "has_checked": has_checked,
            "receipt": receipt,
            "is_closed": is_closed,
            "checked_count": checked_count,
            "missing_estimate_count": missing_estimate_count,
            "focus_price_id": focus_price_id,
        },
    )


@login_required
@require_POST
def add_list_item(request: HttpRequest, shopping_list_id: int) -> HttpResponse:
    shopping_list = _user_list_or_404(request.user, shopping_list_id)
    if _reject_if_closed(request, shopping_list):
        return redirect("shopping_list_detail", shopping_list_id=shopping_list.id)

    name = (request.POST.get("name") or "").strip()
    aisle = (request.POST.get("aisle") or ReferenceItem.AISLE_GROCERY).strip()

    qty_raw = request.POST.get("qty_value") or ""
    unit = (request.POST.get("unit") or UNIT_UNIT).strip()
    note = (request.POST.get("note") or "").strip()

    unit_price_raw = request.POST.get("unit_price") or ""

    qty = None
    unit_price = None

    try:
        qty = _parse_decimal_or_none(qty_raw)
    except (InvalidOperation, ValueError):
        qty = None

    try:
        unit_price = _parse_decimal_or_none(unit_price_raw)
    except (InvalidOperation, ValueError):
        unit_price = None

    qty, unit = _normalize_qty_unit(qty, unit)

    if name:
        it = ListItem.objects.create(
            shopping_list=shopping_list,
            name=name,
            aisle=aisle,
            qty_value=qty,
            unit=unit,
            note=note,
            unit_price=unit_price,
            created_by=request.user,
        )
        it.recompute_estimated_price()
        it.save(update_fields=["estimated_price"])
        messages.success(request, "Item ajouté.")

    return redirect("shopping_list_detail", shopping_list_id=shopping_list.id)


@login_required
@require_POST
def toggle_list_item(request: HttpRequest, item_id: int) -> HttpResponse:
    item = _user_item_or_404(request.user, item_id)
    if _reject_if_closed(request, item.shopping_list):
        return redirect("shopping_list_detail", shopping_list_id=item.shopping_list_id)

    new_state = not item.is_checked
    item.set_checked(request.user, new_state)
    item.save(update_fields=["is_checked", "checked_at", "checked_by"])

    if new_state:
        # focus sur la saisie du prix unitaire
        return redirect(f"/shopping-lists/{item.shopping_list_id}/?focus_price={item.id}")

    return redirect("shopping_list_detail", shopping_list_id=item.shopping_list_id)


@login_required
@require_POST
def update_item_details(request: HttpRequest, item_id: int) -> HttpResponse:
    """
    ✅ Modifie : quantité + unité + note + prix unitaire
    ✅ Recalcule estimated_price = qty × unit_price
    """
    item = _user_item_or_404(request.user, item_id)
    if _reject_if_closed(request, item.shopping_list):
        return redirect("shopping_list_detail", shopping_list_id=item.shopping_list_id)

    qty_raw = request.POST.get("qty_value") or ""
    unit = (request.POST.get("unit") or UNIT_UNIT).strip()
    note = (request.POST.get("note") or "").strip()
    unit_price_raw = (request.POST.get("unit_price") or "").strip()

    qty = None
    unit_price = None

    try:
        qty = _parse_decimal_or_none(qty_raw)
    except (InvalidOperation, ValueError):
        qty = None

    try:
        unit_price = _parse_decimal_or_none(unit_price_raw)
    except (InvalidOperation, ValueError):
        unit_price = None

    qty, unit = _normalize_qty_unit(qty, unit)

    item.qty_value = qty
    item.unit = unit
    item.note = note
    item.unit_price = unit_price

    item.recompute_estimated_price()
    item.save(update_fields=["qty_value", "unit", "note", "unit_price", "estimated_price"])

    # UX: après saisie, focus sur le prochain item coché sans prix
    nxt = _next_checked_missing_estimate(item.shopping_list, exclude_id=item.id)
    if nxt:
        return redirect(f"/shopping-lists/{item.shopping_list_id}/?focus_price={nxt.id}")

    return redirect("shopping_list_detail", shopping_list_id=item.shopping_list_id)


@login_required
@require_POST
def delete_list_item(request: HttpRequest, item_id: int) -> HttpResponse:
    item = _user_item_or_404(request.user, item_id)
    if _reject_if_closed(request, item.shopping_list):
        return redirect("shopping_list_detail", shopping_list_id=item.shopping_list_id)

    shopping_list_id = item.shopping_list_id
    item.delete()
    messages.success(request, "Item supprimé.")
    return redirect("shopping_list_detail", shopping_list_id=shopping_list_id)