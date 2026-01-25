# models.py
from django.db import models
from ckeditor.fields import RichTextField
class Privacy(models.Model):
    title = models.CharField(max_length=200)
    description = RichTextField(verbose_name='Description', help_text='Supports HTML formatting')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title
