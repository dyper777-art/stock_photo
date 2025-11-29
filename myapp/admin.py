from django.contrib import admin
from django.utils.html import format_html
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone
from django.contrib.admin import SimpleListFilter

from .models import SubscriptionPlan, Product, UserSubscription, UserDownloadLog

# -------------------------
# Product admin
# -------------------------
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'subscription_plan', 'image_url', 'file_url')

    def image_url(self, obj):
        if obj.image:
            return obj.image.url
        return "-"
    image_url.short_description = 'Image URL'

    def file_url(self, obj):
        if obj.file:
            return obj.file.url
        return "-"
    file_url.short_description = 'File URL'

# -------------------------
# SubscriptionPlan admin
# -------------------------
@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'daily_limit', 'stripe_price_id', 'price')
    search_fields = ('name',)

# -------------------------
# UserSubscription admin
# -------------------------
class ActiveSubscriptionFilter(admin.SimpleListFilter):
    title = 'Subscription Status'
    parameter_name = 'active_status'

    def lookups(self, request, model_admin):
        return (
            ('active', 'Active'),
            ('expired', 'Expired'),
        )

    def queryset(self, request, queryset):
        today = timezone.now().date()
        if self.value() == 'active':
            return queryset.filter(start_date__lte=today, end_date__gte=today)
        if self.value() == 'expired':
            return queryset.exclude(start_date__lte=today, end_date__gte=today)
        return queryset

@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'is_active', 'start_date', 'end_date', 'downloads_today')
    list_filter = ('start_date', 'end_date', 'plan', ActiveSubscriptionFilter)
    readonly_fields = ('downloads_today',)

    def downloads_today(self, obj):
        return f"{obj.downloads_today()} / {obj.plan.daily_limit if obj.plan else 0}"
    downloads_today.short_description = "Downloads Today / Limit"

    def is_active(self, obj):
        return obj.active()
    is_active.boolean = True
    is_active.short_description = 'Active'

# -------------------------
# UserDownloadLog admin (read-only)
# -------------------------
@admin.register(UserDownloadLog)
class UserDownloadLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'date')
    list_filter = ('date', 'user')
    readonly_fields = ('user', 'product', 'date',)
    search_fields = ('user__username', 'product__name')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

# -------------------------
# Inline for Subscription in UserAdmin
# -------------------------
class SubscriptionInline(admin.StackedInline):
    model = UserSubscription
    can_delete = False
    max_num = 1
    verbose_name_plural = "Subscription Info"
    fields = ('plan', 'downloads_today', 'start_date', 'end_date',)
    readonly_fields = ('downloads_today', 'start_date', 'end_date')

    def downloads_today(self, obj):
        if not obj or not obj.plan:
            return "0"
        return f"{obj.downloads_today()} / {obj.plan.daily_limit}"
    downloads_today.short_description = "Downloads Today / Limit"

# -------------------------
# Inline for Download Logs in UserAdmin
# -------------------------
class UserDownloadLogInline(admin.TabularInline):
    model = UserDownloadLog
    can_delete = False
    verbose_name_plural = 'Download Logs'
    fields = ('product', 'date')
    readonly_fields = ('product', 'date')
    extra = 0

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

# -------------------------
# Custom UserAdmin
# -------------------------
class SubscriptionPlanFilter(SimpleListFilter):
    title = 'Subscription Plan'
    parameter_name = 'plan'

    def lookups(self, request, model_admin):
        plans = SubscriptionPlan.objects.all()
        return [(p.id, p.name) for p in plans]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(usersubscription__plan_id=self.value())
        return queryset

class CustomUserAdmin(BaseUserAdmin):
    fieldsets = (
        ("User Info", {
            "fields": ("username", "email", "is_active", "is_staff", "is_superuser"),
        }),
    )
    inlines = [SubscriptionInline, UserDownloadLogInline]
    list_display = ('username', 'email', 'is_active', 'is_staff', 'subscription_plan_name')
    list_filter = ('is_active', 'is_staff', SubscriptionPlanFilter)
    search_fields = ('username', 'email')

    def subscription_plan_name(self, obj):
        if hasattr(obj, 'usersubscription') and obj.usersubscription.plan:
            return obj.usersubscription.plan.name
        return "No Plan"
    subscription_plan_name.short_description = "Subscription Plan"

# -------------------------
# Register custom UserAdmin
# -------------------------
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
