# core/views_common.py
from __future__ import annotations

from contextlib import contextmanager

from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404

from .models import Household, Membership, ShoppingList


def user_household_or_404(user, household_id: int) -> Household:
    household = get_object_or_404(Household, id=household_id)
    if not Membership.objects.filter(user=user, household=household).exists():
        raise Http404("Household not found")
    return household


@contextmanager
def lock_household(household: Household):
    """
    Verrou pessimiste sur le foyer pour éviter deux listes ouvertes créées en parallèle.
    """
    with transaction.atomic():
        Household.objects.select_for_update().filter(id=household.id).first()
        yield


def get_or_create_open_list(household: Household, *, name: str = "Liste magasin") -> ShoppingList:
    """
    Retourne la ShoppingList ouverte (closed_at IS NULL) la plus récente.
    Sinon en crée une nouvelle.
    """
    with lock_household(household):
        sl = (
            ShoppingList.objects
            .filter(household=household, closed_at__isnull=True)
            .order_by("-created_at", "-id")
            .first()
        )
        if sl:
            return sl
        return ShoppingList.objects.create(household=household, name=name)
