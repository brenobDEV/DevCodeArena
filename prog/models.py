from django.conf import settings
from django.db import models
from .models_accounts import Profile

class Challenge(models.Model):
    company = models.ForeignKey(Profile, on_delete=models.CASCADE, limit_choices_to={"tipo": "company"}, related_name="challenges")
    title = models.CharField(max_length=140)
    description = models.TextField()
    reward = models.DecimalField(max_digits=10, decimal_places=2)
    deadline = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title