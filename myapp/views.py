import os
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template import TemplateDoesNotExist

import resend
import stripe

from .models import Product, UserSubscription, UserDownloadLog, SubscriptionPlan

stripe.api_key = settings.STRIPE_SECRET_KEY

# -------------------------------
# Stripe Helpers
# -------------------------------

def can_subscribe(user, plan_id):
    """
    Returns True if the user can subscribe to the given plan_id.
    Prevents subscribing again to the same active plan.
    """
    subscription = getattr(user, 'usersubscription', None)

    if not subscription:
        return True  # No subscription yet, user can subscribe

    today = timezone.now().date()

    if subscription.plan_id == plan_id and subscription.start_date <= today <= subscription.end_date:
        return False  # User already has this active plan

    return True  # Either different plan or current plan expired



@login_required
def create_checkout_session(request, plan_id):
    if not can_subscribe(request.user, plan_id):
        return HttpResponse("You already have an active subscription this month.", status=400)

    plan = get_object_or_404(SubscriptionPlan, id=plan_id)

    if not plan.stripe_price_id:
        return redirect('subscription_view')

    success_url = request.build_absolute_uri('/success/') + '?session_id={CHECKOUT_SESSION_ID}'
    cancel_url = request.build_absolute_uri('/cancel/')

    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        customer_email=request.user.email,
        mode='subscription',
        line_items=[{
            'price': plan.stripe_price_id,
            'quantity': 1,
        }],
        success_url=success_url,
        cancel_url=cancel_url,
    )

    return redirect(session.url)


@login_required
def subscription_success(request):
    session_id = request.GET.get('session_id')
    if not session_id:
        return HttpResponse("Invalid session", status=400)

    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except stripe.error.InvalidRequestError:
        return HttpResponse("Checkout session not found", status=404)

    stripe_sub_id = session.get("subscription")
    customer_email = session.get("customer_email")
    if not stripe_sub_id or not customer_email:
        return HttpResponse("Invalid session data", status=400)

    try:
        user = User.objects.get(email=customer_email)
    except User.DoesNotExist:
        return HttpResponse("User not found", status=404)

    try:
        line_items = stripe.checkout.Session.list_line_items(session_id, limit=1)
        price_id = line_items.data[0].price.id
    except (IndexError, KeyError):
        return HttpResponse("Could not retrieve line items", status=400)

    try:
        plan = SubscriptionPlan.objects.get(stripe_price_id=price_id)
    except SubscriptionPlan.DoesNotExist:
        return HttpResponse("Plan not found", status=404)

    start_date = timezone.now().date()
    end_date = start_date + timedelta(days=30)
    UserSubscription.objects.update_or_create(
        user=user,
        defaults={
            'plan': plan,
            'stripe_subscription_id': stripe_sub_id,
            'start_date': start_date,
            'end_date': end_date
        }
    )

    return render(request, 'success.html', {'plan': plan})


@login_required
def subscription_cancel(request):
    return render(request, 'cancel.html')


# -------------------------------
# Authentication
# -------------------------------

def login_view(request):
    next_url = request.GET.get('next', '/')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect(request.POST.get('next') or '/')
        return render(request, 'login.html', {'error': 'Invalid credentials', 'next': next_url})
    return render(request, 'login.html', {'next': next_url})


@login_required
def logout_view(request):
    logout(request)
    return redirect('login')


# -------------------------------
# Registration + Activation
# -------------------------------

activation_codes = {}  # For demo; replace with DB in production

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')

        if password != password2:
            return render(request, 'register.html', {'error': 'Passwords do not match'})

        if User.objects.filter(username=username).exists():
            return render(request, 'register.html', {'error': 'Username exists'})

        if User.objects.filter(email=email).exists():
            return render(request, 'register.html', {'error': 'Email exists'})

        user = User.objects.create_user(username=username, email=email, password=password, is_active=False)

        try:
            free_plan = SubscriptionPlan.objects.get(name="Free")
            start_date = timezone.now().date()
            end_date = start_date + timedelta(days=365)
            UserSubscription.objects.create(user=user, plan=free_plan, start_date=start_date, end_date=end_date)
        except SubscriptionPlan.DoesNotExist:
            pass  # optional: handle missing Free plan

        code = get_random_string(20)
        activation_codes[code] = user.username

        activation_link = request.build_absolute_uri(f'/activate/{code}/')
        resend.api_key = settings.RESEND_API_KEY

        try:
            resend.Emails.send({
                "from": settings.MYHOSTEMAIL,
                "to": [email],
                "subject": "Activate your account",
                "html": f"<p>Hello {username},</p><p>Click here to activate: <a href='{activation_link}'>Activate</a></p>"
            })
        except Exception as e:
            print(f"Activation email failed: {e}")
            user.delete()
            return render(request, 'register.html', {'error': 'Could not send activation email.'})

        return render(request, 'check_email.html', {'email': email})

    return render(request, 'register.html')


def activate_view(request, code):
    username = activation_codes.get(code)
    if username:
        user = User.objects.get(username=username)
        user.is_active = True
        user.save()
        del activation_codes[code]
        return render(request, 'activated.html', {'user': user})
    return render(request, 'activation_invalid.html')


# -------------------------------
# Home / Products
# -------------------------------

def home(request):
    products = Product.objects.all()
    return render(request, 'home.html', {'products': products, 'user': request.user})


# -------------------------------
# Download API / File
# -------------------------------

@login_required
def download_product_api(request, product_id):
    user = request.user
    product = get_object_or_404(Product, pk=product_id)
    today = timezone.now().date()

    subscription = getattr(user, 'usersubscription', None)
    if not subscription:
        messages.error(request, "No subscription found.")
        return redirect('home')

    if not subscription.active():
        messages.error(request, "Subscription expired.")
        return redirect('home')

    plan_order = ["Free", "Basic", "Pro"]
    user_plan_name = subscription.plan.name
    product_plan_name = product.subscription_plan.name

    if plan_order.index(product_plan_name) > plan_order.index(user_plan_name):
        messages.error(request, "This product is not included in your subscription.")
        return redirect('home')

    downloads_today = UserDownloadLog.objects.filter(user=user, date=today).count()
    if downloads_today >= subscription.plan.daily_limit:
        messages.error(request, "Daily download limit reached.")
        return redirect('home')

    if not product.file:
        messages.error(request, "File not found.")
        return redirect('home')

    UserDownloadLog.objects.create(user=user, product=product)
    file_handle = product.file.open('rb')
    return FileResponse(file_handle, as_attachment=True, filename=os.path.basename(product.file.name))


# -------------------------------
# Subscription Page
# -------------------------------

@login_required
def subscription_view(request):
    user = request.user
    plans = SubscriptionPlan.objects.all()
    current_subscription = getattr(user, 'usersubscription', None)

    if request.method == "POST":
        plan_id = request.POST.get('plan')
        plan = SubscriptionPlan.objects.get(pk=plan_id)
        start_date = timezone.now().date()
        end_date = start_date + timedelta(days=365)

        UserSubscription.objects.update_or_create(
            user=user,
            defaults={"plan": plan, "start_date": start_date, "end_date": end_date}
        )
        return redirect('subscription_view')

    return render(request, 'subscription.html', {
        'plans': plans,
        'current_subscription': current_subscription
    })


# -------------------------------
# Profile
# -------------------------------

@login_required
def profile_view(request):
    user = request.user
    subscription = getattr(user, 'usersubscription', None)
    downloads_today = 0
    daily_limit = 0

    if subscription:
        today = timezone.now().date()
        downloads_today = UserDownloadLog.objects.filter(user=user, date=today).count()
        daily_limit = subscription.plan.daily_limit

    return render(request, 'profile.html', {
        'subscription': subscription,
        'downloads_today': downloads_today,
        'daily_limit': daily_limit,
    })


# -------------------------------
# Password Reset
# -------------------------------

def password_reset_view(request):
    msg = ""
    alert_type = ""

    if request.method == "POST":
        email = request.POST.get("email")

        if not email:
            msg, alert_type = "Email is required.", "danger"
        else:
            users = User.objects.filter(email=email)
            if not users.exists():
                msg, alert_type = "No account found with that email.", "danger"
            else:
                for user in users:
                    uid = urlsafe_base64_encode(force_bytes(user.pk))
                    token = default_token_generator.make_token(user)
                    reset_url = request.build_absolute_uri(
                        reverse("password_reset_confirm", kwargs={"uidb64": uid, "token": token})
                    )

                    resend.api_key = settings.RESEND_API_KEY
                    try:
                        resend.Emails.send({
                            "from": settings.MYHOSTEMAIL,
                            "to": [user.email],
                            "subject": "Password Reset",
                            "html": f"<p>Hello {user.username},</p>"
                                    f"<p>Reset here: <a href='{reset_url}'>Reset Password</a></p>"
                        })
                    except Exception as e:
                        print(f"Failed to send password reset email: {e}")
                        msg, alert_type = "Failed to send email.", "danger"
                        return render(request, "password_reset_form.html", {"msg": msg, "alert_type": alert_type})

                msg, alert_type = "A password reset link has been sent to your email.", "success"

    return render(request, "password_reset_form.html", {"msg": msg, "alert_type": alert_type})


def password_reset_confirm_view(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        user = None

    if user is None or not default_token_generator.check_token(user, token):
        try:
            return render(request, "password_reset_invalid.html")
        except TemplateDoesNotExist:
            messages.error(request, "Invalid password reset link.")
            return redirect("/")

    if request.method == "POST":
        new_password = request.POST.get("password")
        confirm_password = request.POST.get("password2")
        if not new_password or not confirm_password:
            return render(request, "password_reset_confirm.html", {"error": "Both fields are required."})
        if new_password != confirm_password:
            return render(request, "password_reset_confirm.html", {"error": "Passwords do not match."})

        user.password = make_password(new_password)
        user.save()
        messages.success(request, "Password reset successfully!")
        return redirect("/reset/done/")

    return render(request, "password_reset_confirm.html")


def password_reset_complete_view(request):
    return render(request, 'password_reset_complete.html', {"message": "Your password has been reset successfully."})
