from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .models import Household, Membership


@login_required
def my_households(request):
    memberships = (
        Membership.objects
        .select_related("household")
        .filter(user=request.user)
        .order_by("household__name")
    )
    return render(request, "core/my_households.html", {"memberships": memberships})


@login_required
def create_household(request):
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        if name:
            household = Household.objects.create(name=name, created_by=request.user)
            Membership.objects.create(household=household, user=request.user, role=Membership.ROLE_OWNER)
            return redirect("my_households")

    return render(request, "core/create_household.html")
