"""
Place this file at: core/management/commands/migrate_media_to_supabase.py
(create the management/commands/ folders with empty __init__.py files if they don't exist yet)

Run locally, with your venv active and .env pointing at PRODUCTION Supabase
credentials (so it writes to the same DB Railway uses), from the project root:

    python manage.py migrate_media_to_supabase          # dry run, shows what it would do
    python manage.py migrate_media_to_supabase --apply   # actually uploads + updates DB

This only touches rows whose image_url still looks like an old local path
(starts with /media/ or media/). It reads the actual file from your local
MEDIA_ROOT (since that's the only place these old files still exist),
re-uploads it to the S3/Supabase bucket under the same relative path, and
rewrites image_url to the new public URL via default_storage.url().
"""
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand

from core.models import Achievement, Gallery


class Command(BaseCommand):
    help = "Re-upload old locally-stored media files to Supabase/S3 and fix image_url fields."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Actually upload files and save changes. Without this flag, it's a dry run.",
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]
        models_to_fix = [
            (Gallery, "gallery"),
            (Achievement, "achievements"),
        ]

        total_fixed = 0
        total_missing = 0

        for model, _default_subdir in models_to_fix:
            self.stdout.write(f"\n--- {model.__name__} ---")
            qs = model.objects.filter(image_url__startswith="/media/") | model.objects.filter(
                image_url__startswith="media/"
            )

            for obj in qs:
                old_value = obj.image_url
                relative_path = old_value.split("media/", 1)[-1]  # e.g. "gallery/photo.jpg"
                local_path = Path(settings.MEDIA_ROOT) / relative_path

                if not local_path.exists():
                    self.stdout.write(
                        self.style.WARNING(
                            f"  [MISSING] {model.__name__} id={obj.pk}: "
                            f"local file not found at {local_path} (old value: {old_value})"
                        )
                    )
                    total_missing += 1
                    continue

                self.stdout.write(
                    f"  [{'APPLYING' if apply_changes else 'DRY RUN'}] "
                    f"{model.__name__} id={obj.pk}: {relative_path}"
                )

                if apply_changes:
                    with open(local_path, "rb") as fh:
                        saved_path = default_storage.save(relative_path, File(fh))
                    new_url = default_storage.url(saved_path)
                    obj.image_url = new_url
                    obj.save(update_fields=["image_url"])
                    self.stdout.write(self.style.SUCCESS(f"    -> {new_url}"))
                    total_fixed += 1

        self.stdout.write("\n--- Summary ---")
        self.stdout.write(f"Fixed: {total_fixed}")
        self.stdout.write(f"Missing local file (couldn't fix automatically): {total_missing}")
        if not apply_changes:
            self.stdout.write(
                self.style.WARNING("\nThis was a dry run. Re-run with --apply to actually upload and save.")
            )