from django.apps import apps
from django.test.runner import DiscoverRunner


class UnmanagedModelsTestRunner(DiscoverRunner):
    """
    Every model in `core` is managed=False, pointing at Supabase's
    externally-managed schema — correct for the running app, but it
    means Django's test runner has nothing to build tables from (no
    migrations, and unmanaged models are skipped by schema sync). That
    turns every test into "relation ... does not exist" before it even
    runs.

    This runner flips every core model to managed=True just for the
    lifetime of the throwaway test database, so `manage.py test` gets
    a real schema to work with. Combined with the MIGRATION_MODULES
    override in settings.py (which makes Django treat `core` as an
    unmigrated app during tests), this triggers Django's syncdb path
    instead of looking for migrations that don't exist.
    """

    def setup_databases(self, **kwargs):
        for model in apps.get_app_config("core").get_models():
            model._meta.managed = True
        return super().setup_databases(**kwargs)