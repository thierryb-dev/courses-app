# core/views_receipt.py
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Membership, ShoppingList, Receipt, ReceiptItem

TOLERANCE = Decimal("0.02")


def _user_list_or_404(user, shopping_list_id: int) -> ShoppingList:
    sl = get_object_or_404(ShoppingList, id=shopping_list_id)
    if not Membership.objects.filter(user=user, household=sl.household).exists():
        raise Http404("ShoppingList not found")
    return sl


def _user_receipt_or_404(user, receipt_id: int) -> Receipt:
    receipt = get_object_or_404(Receipt, id=receipt_id)
    if not Membership.objects.filter(user=user, household=receipt.household).exists():
        raise Http404("Receipt not found")
    return receipt


def _enrich_receipt_for_ui(r: Receipt) -> Receipt:
    """
    Attache des attributs calculés directement sur l'instance (utiles en template),
    en supposant que items est prefetch dans la liste.
    """
    r.lines_count = len(r.items.all())  # évite COUNT(*)
    r.actual_total_ui = r.actual_total
    r.estimated_total_ui = r.estimated_total

    r.delta_ui = None
    r.ok_ui = None
    if r.paper_total is not None:
        r.delta_ui = r.actual_total_ui - r.paper_total
        r.ok_ui = abs(r.delta_ui) <= TOLERANCE
    return r


@login_required
def receipt_list(request: HttpRequest) -> HttpResponse:
    """Historique des tickets (tous foyers où l'utilisateur est membre)."""
    qs = (
        Receipt.objects.filter(household__memberships__user=request.user)
        .select_related("household", "shopping_list")
        .prefetch_related("items")
        .distinct()
        .order_by("-purchased_at", "-id")
    )
    receipts = [_enrich_receipt_for_ui(r) for r in qs]
    return render(request, "core/receipt_list.html", {"receipts": receipts, "tolerance": TOLERANCE})


@login_required
@require_POST
def create_receipt(request: HttpRequest, shopping_list_id: int) -> HttpResponse:
    """À la caisse : crée un ticket à partir des items cochés ✅ de la liste ouverte."""
    shopping_list = _user_list_or_404(request.user, shopping_list_id)

    if shopping_list.closed_at is not None:
        messages.error(request, "Cette liste est clôturée. Démarre une nouvelle session.")
        return redirect("shopping_lists")

    # OneToOne reverse
    try:
        existing = shopping_list.receipt
        return redirect("receipt_detail", receipt_id=existing.id)
    except Receipt.DoesNotExist:
        pass

    checked_items = shopping_list.items.filter(is_checked=True).order_by("aisle", "created_at", "id")
    if not checked_items.exists():
        messages.error(request, "Coche au moins un produit pris en rayon avant de créer le ticket.")
        return redirect("shopping_list_detail", shopping_list_id=shopping_list.id)

    with transaction.atomic():
        receipt = Receipt.objects.create(
            household=shopping_list.household,
            shopping_list=shopping_list,
            store_name="",
            paper_total=None,
            purchased_at=timezone.now(),
        )

        lines: list[ReceiptItem] = []
        for pos, it in enumerate(checked_items, start=1):
            lines.append(
                ReceiptItem(
                    receipt=receipt,
                    list_item=it,
                    position=pos,
                    name=it.name,
                    estimated_price=it.estimated_price,
                    # ✅ DEMANDE : par défaut, prix réel = prix saisi en magasin
                    actual_price=it.estimated_price,
                )
            )
        ReceiptItem.objects.bulk_create(lines)

    messages.success(
        request,
        "Ticket créé. Les prix réels sont pré-remplis avec tes estimations : "
        "tu ne modifies que les lignes qui diffèrent, puis tu contrôles/valides."
    )
    return redirect("receipt_detail", receipt_id=receipt.id)


@login_required
def receipt_detail(request: HttpRequest, receipt_id: int) -> HttpResponse:
    receipt = _user_receipt_or_404(request.user, receipt_id)
    items = receipt.items.all().order_by("position", "id")

    estimated_total = receipt.estimated_total
    actual_total = receipt.actual_total
    paper_total = receipt.paper_total

    delta = None
    ok = None
    if paper_total is not None:
        delta = actual_total - paper_total
        ok = abs(delta) <= TOLERANCE

    return render(
        request,
        "core/receipt_detail.html",
        {
            "receipt": receipt,
            "items": items,
            "estimated_total": estimated_total,
            "actual_total": actual_total,
            "paper_total": paper_total,
            "delta": delta,
            "ok": ok,
            "tolerance": TOLERANCE,
        },
    )


@login_required
@require_POST
def update_receipt_header(request: HttpRequest, receipt_id: int) -> HttpResponse:
    receipt = _user_receipt_or_404(request.user, receipt_id)

    store_name = (request.POST.get("store_name") or "").strip()
    purchased_at_raw = (request.POST.get("purchased_at") or "").strip()
    paper_total_raw = (request.POST.get("paper_total") or "").strip().replace(",", ".")

    receipt.store_name = store_name

    # timezone.make_aware() sur datetime-local (naïf)
    if purchased_at_raw:
        try:
            from datetime import datetime

            dt = datetime.fromisoformat(purchased_at_raw)  # "YYYY-MM-DDTHH:MM"
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt, timezone.get_current_timezone())
            receipt.purchased_at = dt
        except Exception:
            messages.error(request, "Date/heure invalide (format attendu : AAAA-MM-JJ HH:MM).")
            return redirect("receipt_detail", receipt_id=receipt.id)

    if paper_total_raw == "":
        receipt.paper_total = None
    else:
        try:
            receipt.paper_total = Decimal(paper_total_raw)
        except (InvalidOperation, ValueError):
            messages.error(request, "Montant total invalide.")
            return redirect("receipt_detail", receipt_id=receipt.id)

    receipt.save(update_fields=["store_name", "purchased_at", "paper_total"])
    messages.success(request, "Ticket mis à jour.")
    return redirect("receipt_detail", receipt_id=receipt.id)


@login_required
@require_POST
def update_receipt_item_price(request: HttpRequest, item_id: int) -> HttpResponse:
    item = get_object_or_404(ReceiptItem, id=item_id)
    receipt = _user_receipt_or_404(request.user, item.receipt_id)

    raw = (request.POST.get("actual_price") or "").strip().replace(",", ".")
    if raw == "":
        item.actual_price = None
    else:
        try:
            item.actual_price = Decimal(raw)
        except (InvalidOperation, ValueError):
            messages.error(request, f"Prix invalide pour « {item.name} ».")
            return redirect("receipt_detail", receipt_id=receipt.id)

    item.save(update_fields=["actual_price"])
    return redirect("receipt_detail", receipt_id=receipt.id)


@login_required
@require_POST
def validate_receipt(request: HttpRequest, receipt_id: int) -> HttpResponse:
    """Contrôle : somme des prix réels vs total caisse. Si OK, clôture la liste."""
    receipt = _user_receipt_or_404(request.user, receipt_id)

    if receipt.paper_total is None:
        messages.error(request, "Renseigne d’abord le montant total du ticket (caisse).")
        return redirect("receipt_detail", receipt_id=receipt.id)

    if receipt.missing_actual_count > 0:
        messages.error(request, "Il manque des prix réels sur certaines lignes.")
        return redirect("receipt_detail", receipt_id=receipt.id)

    with transaction.atomic():
        actual_total = receipt.actual_total
        delta = actual_total - receipt.paper_total

        if abs(delta) <= TOLERANCE:
            if receipt.shopping_list.closed_at is None:
                receipt.shopping_list.closed_at = timezone.now()
                receipt.shopping_list.save(update_fields=["closed_at"])

            messages.success(request, f"Contrôle OK ✅ (écart {delta:.2f} €). Liste clôturée, ticket enregistré.")
            return redirect("receipt_list")

    messages.error(
        request,
        f"Contrôle KO ❌ : somme lignes = {actual_total:.2f} €, total ticket = {receipt.paper_total:.2f} €, écart = {delta:.2f} €.",
    )
    return redirect("receipt_detail", receipt_id=receipt.id)


# ==========================================
# Purge (STAFF) : supprimer tous les tickets
# ==========================================

@staff_member_required
def receipt_purge_confirm(request: HttpRequest) -> HttpResponse:
    """
    Page de confirmation + POST pour supprimer TOUS les tickets.
    Visible uniquement pour les comptes staff.
    """
    receipts_count = Receipt.objects.count()
    items_count = ReceiptItem.objects.count()

    if request.method == "POST":
        with transaction.atomic():
            # Supprime ReceiptItem via cascade, mais on peut supprimer directement Receipt
            Receipt.objects.all().delete()

        messages.success(request, "Tous les tickets ont été supprimés.")
        return redirect("receipt_list")

    return render(
        request,
        "core/receipt_purge_confirm.html",
        {"receipts_count": receipts_count, "items_count": items_count},
    )
