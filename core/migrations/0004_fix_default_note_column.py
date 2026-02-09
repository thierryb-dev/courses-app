from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_listitem_aisle_referenceitem_listitem_reference_item"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=[
                        # Ajoute la colonne si elle n'existe pas (PostgreSQL)
                        """
                        ALTER TABLE core_referenceitem
                        ADD COLUMN IF NOT EXISTS default_note varchar(255) NOT NULL DEFAULT '';
                        """,
                        # Optionnel : enlève le DEFAULT pour coller à un schéma "propre"
                        """
                        ALTER TABLE core_referenceitem
                        ALTER COLUMN default_note DROP DEFAULT;
                        """,
                    ],
                    reverse_sql="""
                        ALTER TABLE core_referenceitem
                        DROP COLUMN IF EXISTS default_note;
                    """,
                ),
            ],
            state_operations=[],
        ),
    ]
