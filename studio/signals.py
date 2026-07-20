from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile


@receiver(post_save, sender=User)
def ensure_profile(sender, instance, created, **kwargs):
    """Every User gets a studio Profile. Superusers default to OWNER."""
    if created:
        role = "OWNER" if instance.is_superuser else "CONTRIBUTOR"
        Profile.objects.get_or_create(user=instance, defaults={"role": role})
