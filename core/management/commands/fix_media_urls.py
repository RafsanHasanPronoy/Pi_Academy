"""
Place at: core/management/commands/fix_media_urls.py

Rewrites any stored URL that points at the Supabase S3-protocol host
(.storage.supabase.co/storage/v1/s3/...) to the public object-download
host (.supabase.co/storage/v1/object/public/...). No files are touched -
they're already in the bucket; only the stored URL strings are wrong.

Run against your PRODUCTION database (i.e. with your real .env active,
since that's what points at the Supabase Postgres DB Railway uses):

    python manage.py fix_media_urls            # dry run
    python manage.py fix_media_urls --apply    # actually save changes
"""
from django.core.management.base import BaseCommand

from core.models import Achievement, Faculty, Gallery, Student

OLD_PREFIX = "https://rhwmfcdvkikyyroknspq.storage.supabase.co/storage/v1/s3/pi-academy-media/"
NEW_PREFIX = "https://rhwmfcdvkikyyroknspq.supabase.co/storage/v1/object/public/pi-academy-media/"

FIELDS = [
    (Achievement, "image_url"),
    (Faculty, "photo_url"),
    (Gallery, "image_url"),
    (Student, "photo_url"),
]


class Command(BaseCommand):
    help = "Rewrite S3-protocol image URLs to public object URLs."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Actually save changes.")

    def handle(self, *args, **options):
        apply_changes = options["apply"]
        total = 0

        for model, field in FIELDS:
            filter_kwargs = {f"{field}__startswith": OLD_PREFIX}
            qs = model.objects.filter(**filter_kwargs)
            count = qs.count()
            if count == 0:
                continue

            self.stdout.write(f"{model.__name__}.{field}: {count} row(s) to fix")

            if apply_changes:
                for obj in qs:
                    old_value = getattr(obj, field)
                    new_value = old_value.replace(OLD_PREFIX, NEW_PREFIX, 1)
                    setattr(obj, field, new_value)
                    obj.save(update_fields=[field])
            total += count

        self.stdout.write(self.style.SUCCESS(f"\n{'Fixed' if apply_changes else 'Would fix'}: {total} row(s)"))
        if not apply_changes and total:
            self.stdout.write(self.style.WARNING("Dry run only. Re-run with --apply to save changes."))