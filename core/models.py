"""
core/models.py

Flux métier :
- Catalogue (ReferenceItem) -> génération de la liste ouverte (ShoppingList + ListItem)
- En rayons :
    - on coche un item quand on le prend
    - on saisit / modifie un prix estimé (poids => estimation puis ajustement)
    - total estimé = somme des estimated_price des items cochés
- Après caisse :
    - on crée un ticket (Receipt) à partir des items cochés
    - on saisit total ticket papier (paper_total)
    - on saisit les prix réels par ligne (ReceiptItem.actual_price)
    - contrôle : somme des lignes == total papier (tolérance)
    - si OK => on clôture la liste (ShoppingList.closed_at)
- Nouvelle session :
    - une nouvelle liste ouverte est créée automatiquement
"""

from __future__ import annotations

from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone

User = settings.AUTH_USER_MODEL


class Household(models.Model):
    name = models.CharField(max_length=120)
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="households_created",
    )
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return self.name


class Membership(models.Model):
    ROLE_OWNER = "owner"
    ROLE_MEMBER = "member"

    ROLE_CHOICES = [
        (ROLE_OWNER, "Propriétaire"),
        (ROLE_MEMBER, "Membre"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_MEMBER)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("user", "household")]

    def __str__(self) -> str:
        return f"{self.user} in {self.household} ({self.role})"


class ReferenceItem(models.Model):
    """
    Catalogue du foyer.
    """

    AISLE_GROCERY = "grocery"
    AISLE_FRUITS_VEG = "fruits_veg"
    AISLE_MEAT_FISH = "meat_fish"
    AISLE_DAIRY = "dairy"
    AISLE_FROZEN = "frozen"
    AISLE_HOUSEHOLD = "household"
    AISLE_OTHER = "other"

    AISLE_CHOICES = [
        (AISLE_GROCERY, "Épicerie"),
        (AISLE_FRUITS_VEG, "Fruits & légumes"),
        (AISLE_MEAT_FISH, "Boucherie / Poissonnerie"),
        (AISLE_DAIRY, "Crèmerie"),
        (AISLE_FROZEN, "Surgelés"),
        (AISLE_HOUSEHOLD, "Entretien"),
        (AISLE_OTHER, "Autre"),
    ]

    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="reference_items")
    name = models.CharField(max_length=140)
    aisle = models.CharField(max_length=30, choices=AISLE_CHOICES, default=AISLE_GROCERY)

    default_quantity = models.CharField(max_length=60, blank=True, default="")
    default_note = models.CharField(max_length=200, blank=True, default="")

    is_active = models.BooleanField(default=True)
    is_selected = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("household", "name")]

    def __str__(self) -> str:
        return self.name


class ShoppingList(models.Model):
    """
    Une session de courses = une ShoppingList.
    Une liste est "ouverte" tant que closed_at est NULL.
    Quand on valide le ticket, on clôture la liste.
    """
    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="shopping_lists")
    name = models.CharField(max_length=120, default="Liste magasin")
    created_at = models.DateTimeField(default=timezone.now)
    closed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        status = "ouverte" if self.closed_at is None else "clôturée"
        return f"{self.household.name} — {self.name} ({status})"

    @property
    def is_open(self) -> bool:
        return self.closed_at is None

    @property
    def estimated_total(self) -> Decimal:
        total = Decimal("0.00")
        for it in self.items.filter(is_checked=True):
            if it.estimated_price is not None:
                total += it.estimated_price
        return total


class ListItem(models.Model):
    shopping_list = models.ForeignKey(ShoppingList, on_delete=models.CASCADE, related_name="items")
    name = models.CharField(max_length=140)
    aisle = models.CharField(max_length=30, choices=ReferenceItem.AISLE_CHOICES, default=ReferenceItem.AISLE_GROCERY)

    quantity = models.CharField(max_length=60, blank=True, default="")
    note = models.CharField(max_length=200, blank=True, default="")

    is_checked = models.BooleanField(default=False)
    checked_at = models.DateTimeField(null=True, blank=True)
    checked_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="checked_list_items"
    )

    estimated_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="list_items_created")
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return self.name

    def set_checked(self, user, checked: bool) -> None:
        self.is_checked = checked
        if checked:
            self.checked_at = timezone.now()
            self.checked_by = user
        else:
            self.checked_at = None
            self.checked_by = None


class Receipt(models.Model):
    """
    Ticket de caisse (dans l'app) : 1 ticket par ShoppingList.
    """
    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="receipts")
    shopping_list = models.OneToOneField(ShoppingList, on_delete=models.CASCADE, related_name="receipt")

    store_name = models.CharField(max_length=160, blank=True, default="")
    purchased_at = models.DateTimeField(default=timezone.now)

    paper_total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return f"Receipt #{self.id} — {self.household.name}"

    @property
    def estimated_total(self) -> Decimal:
        total = Decimal("0.00")
        for it in self.items.all():
            if it.estimated_price is not None:
                total += it.estimated_price
        return total

    @property
    def actual_total(self) -> Decimal:
        total = Decimal("0.00")
        for it in self.items.all():
            if it.actual_price is not None:
                total += it.actual_price
        return total

    @property
    def missing_actual_count(self) -> int:
        return self.items.filter(actual_price__isnull=True).count()


class ReceiptItem(models.Model):
    receipt = models.ForeignKey(Receipt, on_delete=models.CASCADE, related_name="items")

    # 1 ligne par ListItem (évite doublons)
    list_item = models.OneToOneField(ListItem, on_delete=models.CASCADE, related_name="receipt_line")

    position = models.PositiveIntegerField(default=1)
    name = models.CharField(max_length=140)

    estimated_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    actual_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self) -> str:
        return f"{self.position}. {self.name}"
