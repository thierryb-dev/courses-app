from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings
from django.db import models
from django.utils import timezone

User = settings.AUTH_USER_MODEL

# =========================================================
# Units
# =========================================================
UNIT_UNIT = "unit"
UNIT_KG = "kg"
UNIT_G = "g"
UNIT_L = "l"
UNIT_ML = "ml"
UNIT_PACK = "pack"

UNIT_CHOICES = [
    (UNIT_UNIT, "Unité"),
    (UNIT_KG, "Kg"),
    (UNIT_G, "g"),
    (UNIT_L, "L"),
    (UNIT_ML, "mL"),
    (UNIT_PACK, "Pack"),
]


def _format_decimal_human(d: Decimal) -> str:
    s = format(d.normalize(), "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def _money_2(d: Decimal) -> Decimal:
    # arrondi bancaire simple, 2 décimales
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# =========================================================
# Core models
# =========================================================
class Household(models.Model):
    name = models.CharField(max_length=120)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="households_created")
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
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_MEMBER, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("user", "household")]

    def __str__(self) -> str:
        return f"{self.user} in {self.household} ({self.role})"


class ReferenceItem(models.Model):
    """
    Catalogue du foyer — Rayons structurés.
    """

    # 1) Alimentaire
    AISLE_AL_FRUITS_VEG = "al_fruits_veg"
    AISLE_AL_BAKERY = "al_bakery"
    AISLE_AL_STAPLES = "al_staples"
    AISLE_AL_DAIRY = "al_dairy"
    AISLE_AL_MEAT = "al_meat"
    AISLE_AL_FISH = "al_fish"
    AISLE_AL_GROCERY = "al_grocery"
    AISLE_AL_READY = "al_ready"
    AISLE_AL_FROZEN = "al_frozen"

    # 2) Boissons
    AISLE_DR_SOFT = "dr_soft"
    AISLE_DR_ALCOHOL = "dr_alcohol"

    # 3) Hygiène & beauté
    AISLE_HY_BODY = "hy_body"
    AISLE_HY_DAILY = "hy_daily"
    AISLE_HY_HAIR = "hy_hair"

    # 4) Non alimentaire
    AISLE_NF_PROMO = "nf_promo"

    AISLE_CHOICES = [
        (AISLE_AL_FRUITS_VEG, "Alimentaire ▸ Fruits & légumes frais"),
        (AISLE_AL_BAKERY, "Alimentaire ▸ Pains & viennoiseries"),
        (AISLE_AL_STAPLES, "Alimentaire ▸ Œufs, pâtes, riz, conserves"),
        (AISLE_AL_DAIRY, "Alimentaire ▸ Produits laitiers & fromages"),
        (AISLE_AL_MEAT, "Alimentaire ▸ Viandes, charcuteries"),
        (AISLE_AL_FISH, "Alimentaire ▸ Poissons & produits de la mer"),
        (AISLE_AL_GROCERY, "Alimentaire ▸ Épicerie salée & sucrerie"),
        (AISLE_AL_READY, "Alimentaire ▸ Plats préparés & frais réfrigérés"),
        (AISLE_AL_FROZEN, "Alimentaire ▸ Produits surgelés"),
        (AISLE_DR_SOFT, "Boissons ▸ Boissons non alcoolisées (eau, sodas, jus…)"),
        (AISLE_DR_ALCOHOL, "Boissons ▸ Vins, bières, spiritueux"),
        (AISLE_HY_BODY, "Hygiène & beauté ▸ Soins corporels"),
        (AISLE_HY_DAILY, "Hygiène & beauté ▸ Hygiène quotidienne"),
        (AISLE_HY_HAIR, "Hygiène & beauté ▸ Parfums et soins capillaires"),
        (AISLE_NF_PROMO, "Non alimentaire ▸ Offres hebdomadaires / promotions"),
    ]

    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="reference_items")
    name = models.CharField(max_length=140)
    aisle = models.CharField(max_length=40, choices=AISLE_CHOICES, default=AISLE_AL_FRUITS_VEG)

    default_qty_value = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    default_unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default=UNIT_UNIT)
    default_note = models.CharField(max_length=200, blank=True, default="")

    # ✅ NEW: prix unitaire (dans l’unité choisie : €/kg, €/L, €/unité…)
    default_unit_price = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_selected = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("household", "name")]

    def __str__(self) -> str:
        return self.name

    @property
    def unit_label(self) -> str:
        return dict(UNIT_CHOICES).get(self.default_unit, self.default_unit)

    @property
    def quantity_label(self) -> str:
        unit = self.unit_label
        if self.default_qty_value is None:
            return unit
        return f"{_format_decimal_human(self.default_qty_value)} {unit}"

    def compute_default_total(self) -> Decimal | None:
        """
        Total estimé (qté × prix unitaire) si possible.
        """
        if self.default_unit_price is None:
            return None
        qty = self.default_qty_value if self.default_qty_value is not None else Decimal("1")
        return _money_2(qty * self.default_unit_price)


class ShoppingList(models.Model):
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


class ListItem(models.Model):
    shopping_list = models.ForeignKey(ShoppingList, on_delete=models.CASCADE, related_name="items")
    name = models.CharField(max_length=140)
    aisle = models.CharField(
        max_length=40,
        choices=ReferenceItem.AISLE_CHOICES,
        default=ReferenceItem.AISLE_AL_FRUITS_VEG,
    )

    qty_value = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default=UNIT_UNIT)
    note = models.CharField(max_length=200, blank=True, default="")

    is_checked = models.BooleanField(default=False)
    checked_at = models.DateTimeField(null=True, blank=True)
    checked_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="checked_list_items")

    # ✅ NEW: prix unitaire estimé
    unit_price = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)

    # ✅ On conserve ce champ comme "prix total estimé" (compatibilité UI/Receipt)
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

    @property
    def unit_label(self) -> str:
        return dict(UNIT_CHOICES).get(self.unit, self.unit)

    @property
    def quantity_label(self) -> str:
        unit = self.unit_label
        if self.qty_value is None:
            return unit
        return f"{_format_decimal_human(self.qty_value)} {unit}"

    def compute_total(self) -> Decimal | None:
        if self.unit_price is None:
            return None
        qty = self.qty_value if self.qty_value is not None else Decimal("1")
        return _money_2(qty * self.unit_price)

    def recompute_estimated_price(self) -> None:
        """
        Synchronise estimated_price avec qty × unit_price.
        """
        total = self.compute_total()
        self.estimated_price = total


class Receipt(models.Model):
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
        s = Decimal("0.00")
        for it in self.items.all():
            if it.estimated_price is not None:
                s += it.estimated_price
        return s

    @property
    def actual_total(self) -> Decimal:
        s = Decimal("0.00")
        for it in self.items.all():
            if it.actual_price is not None:
                s += it.actual_price
        return s

    @property
    def missing_actual_count(self) -> int:
        return sum(1 for it in self.items.all() if it.actual_price is None)


class ReceiptItem(models.Model):
    receipt = models.ForeignKey(Receipt, on_delete=models.CASCADE, related_name="items")
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