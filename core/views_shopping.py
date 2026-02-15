from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Household, ListItem, Membership, ShoppingList, ReferenceItem, Receipt
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
    """Return True if rejected (closed) and the caller should redirect."""
    if shopping_list.closed_at is not None:
        messages.error(request, "Cette liste est clôturée : aucune modification n'est autorisée.")
        return True
    return False


@login_required
def shopping_lists(request: HttpRequest) -> HttpResponse:
    households = Household.objects.filter(memberships__user=request.user).distinct().order_by("name")

    # UX actuelle: 1 liste ouverte par foyer, créée au besoin
    open_lists = [get_or_create_open_list(h) for h in households]

    return render(request, "core/shopping_lists.html", {"lists": open_lists})


@login_required
def shopping_list_detail(request: HttpRequest, shopping_list_id: int) -> HttpResponse:
    shopping_list = _user_list_or_404(request.user, shopping_list_id)
    items = shopping_list.items.all().order_by("aisle", "is_checked", "created_at", "id")

    running_total = Decimal("0.00")
    for it in items:
        if it.is_checked and it.estimated_price is not None:
            running_total += it.estimated_price

    has_checked = shopping_list.items.filter(is_checked=True).exists()

    try:
        receipt = shopping_list.receipt
    except Receipt.DoesNotExist:
        receipt = None

    is_closed = shopping_list.closed_at is not None

    return render(
        request,
        "core/shopping_list_detail.html",
        {
            "shopping_list": shopping_list,
            "items": items,
            "running_total": running_total,
            "aisle_choices": ReferenceItem.AISLE_CHOICES,
            "has_checked": has_checked,
            "receipt": receipt,
            "is_closed": is_closed,
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
    quantity = (request.POST.get("quantity") or "").strip()
    note = (request.POST.get("note") or "").strip()

    if name:
        ListItem.objects.create(
            shopping_list=shopping_list,
            name=name,
            aisle=aisle,
            quantity=quantity,
            note=note,
            created_by=request.user,
        )

    return redirect("shopping_list_detail", shopping_list_id=shopping_list.id)


@login_required
@require_POST
def toggle_list_item(request: HttpRequest, item_id: int) -> HttpResponse:
    item = _user_item_or_404(request.user, item_id)
    if _reject_if_closed(request, item.shopping_list):
        return redirect("shopping_list_detail", shopping_list_id=item.shopping_list_id)

    item.set_checked(request.user, not item.is_checked)
    item.save(update_fields=["is_checked", "checked_at", "checked_by"])
    return redirect("shopping_list_detail", shopping_list_id=item.shopping_list_id)


@login_required
@require_POST
def update_estimated_price(request: HttpRequest, item_id: int) -> HttpResponse:
    item = _user_item_or_404(request.user, item_id)
    if _reject_if_closed(request, item.shopping_list):
        return redirect("shopping_list_detail", shopping_list_id=item.shopping_list_id)

    raw = (request.POST.get("estimated_price") or "").strip().replace(",", ".")
    if raw == "":
        item.estimated_price = None
    else:
        try:
            item.estimated_price = Decimal(raw)
        except (InvalidOperation, ValueError):
            messages.error(request, "Prix estimé invalide.")
            return redirect("shopping_list_detail", shopping_list_id=item.shopping_list_id)

    item.save(update_fields=["estimated_price"])
    return redirect("shopping_list_detail", shopping_list_id=item.shopping_list_id)


@login_required
@require_POST
def delete_list_item(request: HttpRequest, item_id: int) -> HttpResponse:
    item = _user_item_or_404(request.user, item_id)
    if _reject_if_closed(request, item.shopping_list):
        return redirect("shopping_list_detail", shopping_list_id=item.shopping_list_id)

    shopping_list_id = item.shopping_list_id
    item.delete()
    return redirect("shopping_list_detail", shopping_list_id=shopping_list_id)
