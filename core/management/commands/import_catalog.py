import json
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import Household, ReferenceItem


class Command(BaseCommand):
    help = "Importe un catalogue (ReferenceItem) depuis un JSON dans un Household donné."

    def add_arguments(self, parser):
        parser.add_argument("json_path", type=str, help="Chemin vers le fichier JSON (catalog_base.json)")
        parser.add_argument("--household-id", type=int, required=True, help="ID du foyer cible (ex: 2)")
        parser.add_argument(
            "--mode",
            choices=["upsert", "replace"],
            default="upsert",
            help="upsert = crée/maj, replace = supprime le catalogue puis importe",
        )
        parser.add_argument(
            "--overwrite-price",
            action="store_true",
            help="Écrase default_unit_price même si déjà renseigné.",
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        json_path = Path(opts["json_path"])
        household_id = opts["household_id"]
        mode = opts["mode"]
        overwrite_price = opts["overwrite_price"]

        if not json_path.exists():
            raise CommandError(f"Fichier introuvable: {json_path}")

        household = Household.objects.filter(id=household_id).first()
        if household is None:
            raise CommandError(f"Household id={household_id} introuvable")

        payload = json.loads(json_path.read_text(encoding="utf-8"))
        items = payload.get("items")
        if not isinstance(items, list):
            raise CommandError("JSON invalide: clé 'items' attendue (liste)")

        if mode == "replace":
            deleted, _ = ReferenceItem.objects.filter(household=household).delete()
            self.stdout.write(self.style.WARNING(f"Catalogue supprimé: {deleted} objets supprimés."))

        def _dec(x):
            return None if x is None or x == "" else Decimal(str(x))

        created = 0
        updated = 0

        for it in items:
            name = (it.get("name") or "").strip()
            if not name:
                continue

            aisle = it.get("aisle", ReferenceItem.AISLE_AL_FRUITS_VEG)
            default_unit = it.get("default_unit", "unit")

            unit_price = _dec(it.get("default_unit_price"))
            qty_value = _dec(it.get("default_qty_value"))
            note = it.get("default_note", "")

            obj, was_created = ReferenceItem.objects.get_or_create(
                household=household,
                name=name,
                defaults={
                    "aisle": aisle,
                    "default_unit": default_unit,
                    "default_unit_price": unit_price,
                    "default_qty_value": qty_value,
                    "default_note": note,
                    "is_active": True,
                },
            )

            if was_created:
                created += 1
                continue

            dirty = False

            if obj.aisle != aisle:
                obj.aisle = aisle
                dirty = True
            if obj.default_unit != default_unit:
                obj.default_unit = default_unit
                dirty = True
            if qty_value is not None and obj.default_qty_value != qty_value:
                obj.default_qty_value = qty_value
                dirty = True
            if note and obj.default_note != note:
                obj.default_note = note
                dirty = True

            if unit_price is not None:
                if overwrite_price or obj.default_unit_price is None:
                    if obj.default_unit_price != unit_price:
                        obj.default_unit_price = unit_price
                        dirty = True

            if dirty:
                obj.save()
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Import terminé pour household={household_id}: created={created}, updated={updated}"
        ))