import hashlib
import os
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# -----------------------
# File Upload Helper
# -----------------------
def md5_file_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    timestamp = timezone.now().strftime("%Y%m%d%H%M%S%f")
    hash_input = f"{filename}{timestamp}".encode('utf-8')
    md5_name = hashlib.md5(hash_input).hexdigest()
    return os.path.join('uploads/images/', f"{md5_name}.{ext}")

# -----------------------
# Subscription Plan
# -----------------------
class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    stripe_price_id = models.CharField(max_length=100, blank=True, null=True)
    daily_limit = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name

# -----------------------
# Product
# -----------------------
class Product(models.Model):
    name = models.CharField(max_length=100)
    subscription_plan = models.ForeignKey(
        SubscriptionPlan, on_delete=models.CASCADE, related_name="products", default=1
    )
    image = models.ImageField(upload_to=md5_file_upload_path, blank=True, null=True)
    file = models.FileField(upload_to=md5_file_upload_path, blank=True, null=True)

    def __str__(self):
        return self.name

# -----------------------
# User Subscription
# -----------------------
class UserSubscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="usersubscription")
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True, null=True)
    start_date = models.DateField(auto_now_add=True)
    end_date = models.DateField()

    def active(self):
        today = timezone.now().date()
        return self.start_date <= today <= self.end_date

    def downloads_today(self):
        today = timezone.now().date()
        return UserDownloadLog.objects.filter(user=self.user, date=today).count()

    def __str__(self):
        plan_name = self.plan.name if self.plan else "No Plan"
        return f"{self.user.username} - {plan_name}"

    def paid_this_month(self):
        today = timezone.now().date()
        return self.start_date.year == today.year and self.start_date.month == today.month

# -----------------------
# User Download Log
# -----------------------
class UserDownloadLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = "User Download Log"
        verbose_name_plural = "User Download Logs"

    def __str__(self):
        user_name = self.user.username if self.user else "Unknown User"
        return f"{user_name} downloaded {self.product.name} on {self.date}"
