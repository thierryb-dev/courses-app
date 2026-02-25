from django.conf import settings
from django.db import models
from django.utils import timezone


# =========================================================
# Household / Membership
# =========================================================

class Household(models.Model):
    name = models.CharField(max_length=120)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_households",
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Membership(models.Model):
    ROLE_OWNER = "owner"
    ROLE_MEMBER = "member"

    ROLE_CHOICES = [
        (ROLE_OWNER, "Owner"),
        (ROLE_MEMBER, "Member"),
    ]

    household = models.ForeignKey(
        Household,
        on_delete=models.CASCADE,
        related_name="memberships",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_MEMBER,
    )

    joined_at = models.DateTimeField(
        auto_now_add=True,
        null=True,
        blank=True,
    )

    class Meta:
        unique_together = [("household", "user")]
        ordering = ["-joined_at"]

    def __str__(self):
        return f"{self.user} in {self.household} ({self.role})"


# =========================================================
# Reference (catalog) items with aisle/category
# =========================================================

class ReferenceItem(models.Model):
    """
    Catalogue par foyer (liste de référence).
    Ajout d'un rayon (aisle) pour trier en magasin.
    """

    AISLE_PRODUCE = "produce"     # fruits/légumes
    AISLE_FRESH = "fresh"         # frais (crèmerie, charcuterie…)
    AISLE_MEAT_FISH = "meatfish"  # viande/poisson
    AISLE_GROCERY = "grocery"     # épicerie
    AISLE_FROZEN = "frozen"       # surgelés
    AISLE_BAKERY = "bakery"       # boulangerie
    AISLE_DRINKS = "drinks"       # boissons
    AISLE_HYGIENE = "hygiene"     # hygiène/beauty
    AISLE_HOME = "home"           # entretien/maison
    AISLE_OTHER = "other"         # autres

    AISLE_CHOICES = [
        (AISLE_PRODUCE, "Fruits & légumes"),
        (AISLE_FRESH, "Frais"),
        (AISLE_MEAT_FISH, "Viande & poisson"),
        (AISLE_GROCERY, "Épicerie"),
        (AISLE_FROZEN, "Surgelés"),
        (AISLE_BAKERY, "Boulangerie"),
        (AISLE_DRINKS, "Boissons"),
        (AISLE_HYGIENE, "Hygiène"),
        (AISLE_HOME, "Maison"),
        (AISLE_OTHER, "Autres"),
    ]

    AISLE_ORDER = {
        AISLE_PRODUCE: 10,
        AISLE_FRESH: 20,
        AISLE_MEAT_FISH: 30,
        AISLE_GROCERY: 40,
        AISLE_FROZEN: 50,
        AISLE_BAKERY: 60,
        AISLE_DRINKS: 70,
        AISLE_HYGIENE: 80,
        AISLE_HOME: 90,
        AISLE_OTHER: 999,
    }

    household = models.ForeignKey(
        Household,
        on_delete=models.CASCADE,
        related_name="reference_items",
    )

    name = models.CharField(max_length=160)
    aisle = models.CharField(max_length=20, choices=AISLE_CHOICES, default=AISLE_GROCERY)

    default_quantity = models.CharField(max_length=50, blank=True)
    default_note = models.CharField(max_length=255, blank=True)

    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_reference_items",
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        unique_together = [("household", "name")]

    def __str__(self):
        return f"{self.name} ({self.household})"

    @property
    def aisle_rank(self) -> int:
        return self.AISLE_ORDER.get(self.aisle, 999)


# =========================================================
# Shopping Lists
# =========================================================

class ShoppingList(models.Model):
    household = models.ForeignKey(
        Household,
        on_delete=models.CASCADE,
        related_name="shopping_lists",
    )

    name = models.CharField(max_length=120)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_shopping_lists",
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("household", "name")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.household})"


class ListItem(models.Model):
    shopping_list = models.ForeignKey(
        ShoppingList,
        on_delete=models.CASCADE,
        related_name="items",
    )

    # lien optionnel vers le catalogue
    reference_item = models.ForeignKey(
        ReferenceItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="list_items",
    )

    # snapshot (indépendant du catalogue)
    name = models.CharField(max_length=160)
    aisle = models.CharField(max_length=20, choices=ReferenceItem.AISLE_CHOICES, default=ReferenceItem.AISLE_GROCERY)
    quantity = models.CharField(max_length=50, blank=True)
    note = models.CharField(max_length=255, blank=True)

    is_checked = models.BooleanField(default=False)

    checked_at = models.DateTimeField(null=True, blank=True)

    checked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="checked_list_items",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_list_items",
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["is_checked", "-created_at"]

    def __str__(self):
        return self.name

    def set_checked(self, user, checked: bool):
        self.is_checked = checked
        if checked:
            self.checked_at = timezone.now()
            self.checked_by = user
        else:
            self.checked_at = None
            self.checked_by = None
