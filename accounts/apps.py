from django.apps import AppConfig

class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    # This ready() method is the magic key that wakes up your signals
    def ready(self):
        import accounts.signals