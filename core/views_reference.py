from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from .models import Household, Membership, ReferenceItem, ShoppingList, ListItem


def _user_household_or_404(user, household_id: int) -> Household:
    household = get_object_or_404(Household, id=household_id)
    if not Membership.objects.filter(user=user, household=household).exists():
        raise Http404("Household not found")
    return household


@login_required
def reference_list(request, household_id: int):
    household = _user_household_or_404(request.user, household_id)

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        aisle = (request.POST.get("aisle") or ReferenceItem.AISLE_GROCERY).strip()
        qty = (request.POST.get("default_quantity") or "").strip()
        note = (request.POST.get("default_note") or "").strip()

        if name:
            # get_or_create évite les doublons
            ReferenceItem.objects.get_or_create(
                household=household,
                name=name,
                defaults={
                    "aisle": aisle,
                    "default_quantity": qty,
                    "default_note": note,
                    "created_by": request.user,
                },
            )
        return redirect("reference_list", household_id=household.id)

    items = ReferenceItem.objects.filter(household=household).order_by("name")
    return render(
        request,
        "core/reference_list.html",
        {
            "household": household,
            "items": items,
            "aisle_choices": ReferenceItem.AISLE_CHOICES,
        },
    )


@login_required
def reference_toggle_active(request, item_id: int):
    item = get_object_or_404(ReferenceItem, id=item_id)
    if not Membership.objects.filter(user=request.user, household=item.household).exists():
        raise Http404("Not found")

    item.is_active = not item.is_active
    item.save(update_fields=["is_active"])
    return redirect("reference_list", household_id=item.household.id)


@login_required
def generate_shopping_list_from_reference(request, household_id: int):
    household = _user_household_or_404(request.user, household_id)
    ref_items = ReferenceItem.objects.filter(household=household, is_active=True).order_by("name")

    if request.method == "POST":
        list_name = (request.POST.get("list_name") or "").strip() or "Courses"
        selected_ids = request.POST.getlist("ref_item")
        shopping_list, created = ShoppingList.objects.get_or_create(
            household=household,
            name=list_name,
            defaults={"created_by": request.user},
        )

        # Régénération : évite doublons
        shopping_list.items.all().delete()
        selected = ref_items.filter(id__in=selected_ids)
        bulk = []
        for r in selected:
            bulk.append(
                ListItem(
                    shopping_list=shopping_list,
                    reference_item=r,
                    name=r.name,
                    aisle=r.aisle,
                    quantity=r.default_quantity,
                    note=r.default_note,
                    created_by=request.user,
                )
            )
        if bulk:
            ListItem.objects.bulk_create(bulk)

        return redirect("shopping_list_detail", list_id=shopping_list.id)

    return render(
        request,
        "core/reference_select.html",
        {
            "household": household,
            "ref_items": ref_items,
        },
    )



