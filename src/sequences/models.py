from django.db import models
from django.utils.translation import gettext_lazy as _


class Sequence(models.Model):

    name = models.CharField(
        verbose_name=_("name"),
        max_length=100,
        primary_key=True,
    )

    last = models.PositiveBigIntegerField(
        verbose_name=_("last value"),
    )

    class Meta:
        verbose_name = _("sequence")
        verbose_name_plural = _("sequences")

    def __str__(self):
        return f"Sequence(name={self.name!r}, last={self.last!r})"
