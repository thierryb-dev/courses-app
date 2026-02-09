from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from .models import Household, Membership, ShoppingList, ListItem, ReferenceItem


def _user_household_or_404(user, household_id: int) -> Household:
    household = get_object_or_404(Household, id=household_id)
    if not Membership.objects.filter(user=user, household=household).exists():
        raise Http404("Household not found")
    return household


def _user_list_or_404(user, list_id: int) -> ShoppingList:
    shopping_list = get_object_or_404(ShoppingList, id=list_id)
    if not Membership.objects.filter(user=user, household=shopping_list.household).exists():
        raise Http404("Shopping list not found")
    return shopping_list


@login_required
def shopping_lists(request):
    household_id = request.GET.get("household")

    qs = (
        ShoppingList.objects
        .filter(household__memberships__user=request.user)
        .select_related("household")
        .distinct()
        .order_by("-created_at")
    )

    selected_household = None
    if household_id:
        selected_household = _user_household_or_404(request.user, int(household_id))
        qs = qs.filter(household=selected_household)

    households = Household.objects.filter(memberships__user=request.user).order_by("name").distinct()

    return render(
        request,
        "core/shopping_lists.html",
        {"shopping_lists": qs, "households": households, "selected_household": selected_household},
    )


@login_required
def create_shopping_list(request, household_id: int):
    household = _user_household_or_404(request.user, household_id)

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        if name:
            ShoppingList.objects.create(household=household, name=name, created_by=request.user)
            return redirect("shopping_lists")

    return render(request, "core/shopping_list_create.html", {"household": household})


@login_required
def shopping_list_detail(request, list_id: int):
    shopping_list = _user_list_or_404(request.user, list_id)

    # tri par rayon (ordre défini) puis nom, en gardant non-cochés en haut
    # on ne peut pas facilement "order by mapping" en pur ORM sans case/when;
    # on fait simple: on trie en Python avec le ranking.
    items = list(shopping_list.items.all())
    rank = ReferenceItem.AISLE_ORDER

    def sort_key(it: ListItem):
        return (it.is_checked, rank.get(it.aisle, 999), it.name.lower())

    items.sort(key=sort_key)

    return render(
        request,
        "core/shopping_list_detail.html",
        {"shopping_list": shopping_list, "items": items, "aisle_choices": ReferenceItem.AISLE_CHOICES},
    )


@login_required
def add_list_item(request, list_id: int):
    shopping_list = _user_list_or_404(request.user, list_id)

    if request.method == "POST":
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

    return redirect("shopping_list_detail", list_id=shopping_list.id)


@login_required
def toggle_list_item(request, item_id: int):
    item = get_object_or_404(ListItem, id=item_id)
    if not Membership.objects.filter(user=request.user, household=item.shopping_list.household).exists():
        raise Http404("Item not found")

    item.set_checked(request.user, not item.is_checked)
    item.save(update_fields=["is_checked", "checked_at", "checked_by"])

    return redirect("shopping_list_detail", list_id=item.shopping_list.id)


@login_required
def delete_list_item(request, item_id: int):
    item = get_object_or_404(ListItem, id=item_id)
    if not Membership.objects.filter(user=request.user, household=item.shopping_list.household).exists():
        raise Http404("Item not found")

    list_id = item.shopping_list.id
    if request.method == "POST":
        item.delete()

    return redirect("shopping_list_detail", list_id=list_id)


@login_required
def clear_checked_items(request, list_id: int):
    shopping_list = _user_list_or_404(request.user, list_id)

    if request.method == "POST":
        shopping_list.items.filter(is_checked=True).delete()

    return redirect("shopping_list_detail", list_id=shopping_list.id)
