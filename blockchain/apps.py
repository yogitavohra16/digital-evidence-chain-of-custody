"""App configuration for the blockchain app."""
from django.apps import AppConfig
from django.db.models.signals import post_migrate


def create_genesis_after_migrate(sender, **kwargs):
    """Create the genesis block once, right after the database tables exist.

    Why a post_migrate signal: Django sends this signal after `python manage.py migrate`
    finishes. At that moment the tables exist, so we can safely make sure block 0 is
    present. The function is idempotent: if the chain already has blocks it does
    nothing, so the genesis block is never duplicated and nothing is rewritten.
    """
    from .services import ensure_genesis_block

    ensure_genesis_block()


class BlockchainConfig(AppConfig):
    """Registers the 'blockchain' app (block table and chain services)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "blockchain"
    verbose_name = "Custody Blockchain"

    def ready(self):
        """Connect the post_migrate hook when Django starts."""
        post_migrate.connect(create_genesis_after_migrate, sender=self)
