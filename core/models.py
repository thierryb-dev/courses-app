from django.conf import settings
from django.db import models
from django.utils import timezone


class Household(models.Model):
    name = models.CharField(max_length=120)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return self.name


class Membership(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        MEMBER = "member", "Member"

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
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)

    # Tu avais déjà created_at → on le garde
    created_at = models.DateTimeField(default=timezone.now)

    # ✅ champ manquant, nécessaire pour ton filtre dans la vue
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "household"], name="uniq_user_household"),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user} -> {self.household} ({self.role})"
