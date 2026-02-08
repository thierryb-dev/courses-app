from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from .models import Household, Membership


@login_required
def my_households(request):
    # On récupère les memberships (avec le household associé) pour afficher aussi le rôle
    memberships = (
        Membership.objects
        .select_related("household")
        .filter(user=request.user, is_active=True)
        .order_by("household__name")
    )
    return render(request, "core/my_households.html", {"memberships": memberships})


@login_required
def create_household(request):
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        if name:
            household = Household.objects.create(name=name, created_at=timezone.now())

            # Crée automatiquement le lien (Membership) en Owner
            Membership.objects.create(
                household=household,
                user=request.user,
                role=Membership.Role.OWNER,
                is_active=True,
                created_at=timezone.now(),
            )

            return redirect("my_households")

    return render(request, "core/create_household.html")
