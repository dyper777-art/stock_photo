from django.contrib import admin
from django.urls import path
from myapp import views

from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Public pages
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('activate/<str:code>/', views.activate_view, name='activate'),

    # Download product (requires login)
    path('download/<int:product_id>/', views.download_product_api, name='download_product'),

    # Password reset
    path("password_reset/", views.password_reset_view, name="password_reset"),


        path(
        "reset/<uidb64>/<token>/",
        views.password_reset_confirm_view,
        name="password_reset_confirm"
    ),

    path('reset/done/', views.password_reset_complete_view, name='password_reset_complete'),

    path('subscription/', views.subscription_view, name='subscriptions'),

    path('create_checkout/<int:plan_id>/', views.create_checkout_session, name='create_checkout'),
    path('success/', views.subscription_success, name='checkout_success'),
    path('cancel/', views.subscription_cancel, name='checkout_cancel'),

    path('profile/', views.profile_view, name='profile'),


]



if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
