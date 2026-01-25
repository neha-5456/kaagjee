"""
CloudServices India - Blog Models
"""
from django.db import models
from django.utils.text import slugify
from apps.accounts.models import User


class BlogPost(models.Model):
    """Blog Post Model"""
    
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PUBLISHED = 'published', 'Published'
        ARCHIVED = 'archived', 'Archived'

    title = models.CharField(max_length=300)
    slug = models.SlugField(unique=True, max_length=350)
    content = models.TextField()
    excerpt = models.CharField(max_length=500, blank=True)
    featured_image = models.ImageField(upload_to='blog/', null=True, blank=True)
    
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blog_posts')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    
    # SEO
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(blank=True)
    
    # Stats
    views_count = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Blog Post'
        verbose_name_plural = 'Blog Posts'

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


class BlogCategory(models.Model):
    """Blog Category Model"""
    
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, max_length=120)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Blog Category'
        verbose_name_plural = 'Blog Categories'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class BlogTag(models.Model):
    """Blog Tag Model"""
    
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True, max_length=60)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Blog Tag'
        verbose_name_plural = 'Blog Tags'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


# Add relationships to BlogPost
BlogPost.add_to_class('categories', models.ManyToManyField(BlogCategory, blank=True, related_name='posts'))
BlogPost.add_to_class('tags', models.ManyToManyField(BlogTag, blank=True, related_name='posts'))