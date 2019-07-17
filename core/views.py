from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, get_object_or_404, HttpResponse
from django.views.generic import ListView, DetailView, View
from django.shortcuts import redirect
from django.utils import timezone
from .forms import CheckoutForm, CouponForm, RefundForm
from .models import Item, OrderItem, Order, Address, Payment, Coupon, Refund
from django.db.models import Q
from eternalindia.utils import transact,generate_client_token
import stripe
import random
import string
stripe.api_key = settings.STRIPE_SECRET_KEY


#def unique_code_generator():
#   return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))

def unique_code_generator():
    order_new_id = random_string_generator()
    print(order_new_id)
    qs_exists = Order.objects.filter(ref_code=order_new_id).exists()
    if qs_exists:
        return unique_code_generator()
    return order_new_id


def random_string_generator():
   return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))

'''
def unique_order_id_generator(instance):
    order_new_id = random_string_generator()

    #Klass = instance.__class__
    qs_exists = Order.objects.filter(ref_id=order_new_id).exists()
    if qs_exists:
        return unique_order_id_generator(instance)
    return order_new_id'''


def products(request):
    context = {
        'items': Item.objects.all()
    }
    return render(request, "products.html", context)


def is_valid_form(values):
    valid = True
    for field in values:
        if field == '':
            valid = False
    return valid


class CheckoutView(View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            form = CheckoutForm()
            context = {
                'form': form,
                'couponform': CouponForm(),
                'order': order,
                'DISPLAY_COUPON_FORM': True
            }

            shipping_address_qs = Address.objects.filter(
                user=self.request.user,
                address_type='S',
                default=True
            )
            if shipping_address_qs.exists():
                context.update(
                    {'default_shipping_address': shipping_address_qs[0]})

            billing_address_qs = Address.objects.filter(
                user=self.request.user,
                address_type='B',
                default=True
            )
            if billing_address_qs.exists():
                context.update(
                    {'default_billing_address': billing_address_qs[0]})

            return render(self.request, "checkout.html", context)
        except ObjectDoesNotExist:
            messages.info(self.request, "You do not have an active order")
            return redirect("core:checkout")

    def post(self, *args, **kwargs):
        form = CheckoutForm(self.request.POST or None)
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            if form.is_valid():

                use_default_shipping = form.cleaned_data.get(
                    'use_default_shipping')
                if use_default_shipping:
                    print("Using the defualt shipping address")
                    address_qs = Address.objects.filter(
                        user=self.request.user,
                        address_type='S',
                        default=True
                    )
                    if address_qs.exists():
                        shipping_address = address_qs[0]
                        order.shipping_address = shipping_address
                        order.save()
                    else:
                        messages.info(
                            self.request, "No default shipping address available")
                        return redirect('core:checkout')
                else:
                    print("User is entering a new shipping address")
                    shipping_address1 = form.cleaned_data.get(
                        'shipping_address')
                    shipping_address2 = form.cleaned_data.get(
                        'shipping_address2')
                    shipping_country = form.cleaned_data.get(
                        'shipping_country')
                    shipping_zip = form.cleaned_data.get('shipping_zip')

                    if is_valid_form([shipping_address1, shipping_country, shipping_zip]):
                        shipping_address = Address(
                            user=self.request.user,
                            street_address=shipping_address1,
                            apartment_address=shipping_address2,
                            country=shipping_country,
                            zip=shipping_zip,
                            address_type='S'
                        )
                        shipping_address.save()

                        order.shipping_address = shipping_address
                        order.save()

                        set_default_shipping = form.cleaned_data.get(
                            'set_default_shipping')
                        if set_default_shipping:
                            shipping_address.default = True
                            shipping_address.save()

                    else:
                        messages.info(
                            self.request, "Please fill in the required shipping address fields")

                use_default_billing = form.cleaned_data.get(
                    'use_default_billing')
                same_billing_address = form.cleaned_data.get(
                    'same_billing_address')

                if same_billing_address:
                    billing_address = shipping_address
                    billing_address.pk = None
                    billing_address.save()
                    billing_address.address_type = 'B'
                    billing_address.save()
                    order.billing_address = billing_address
                    order.save()

                elif use_default_billing:
                    print("Using the defualt billing address")
                    address_qs = Address.objects.filter(
                        user=self.request.user,
                        address_type='B',
                        default=True
                    )
                    if address_qs.exists():
                        billing_address = address_qs[0]
                        order.billing_address = billing_address
                        order.save()
                    else:
                        messages.info(
                            self.request, "No default billing address available")
                        return redirect('core:checkout')
                else:
                    print("User is entering a new billing address")
                    billing_address1 = form.cleaned_data.get(
                        'billing_address')
                    billing_address2 = form.cleaned_data.get(
                        'billing_address2')
                    billing_country = form.cleaned_data.get(
                        'billing_country')
                    billing_zip = form.cleaned_data.get('billing_zip')

                    if is_valid_form([billing_address1, billing_country, billing_zip]):
                        billing_address = Address(
                            user=self.request.user,
                            street_address=billing_address1,
                            apartment_address=billing_address2,
                            country=billing_country,
                            zip=billing_zip,
                            address_type='B'
                        )
                        billing_address.save()

                        order.billing_address = billing_address
                        order.save()

                        set_default_billing = form.cleaned_data.get(
                            'set_default_billing')
                        if set_default_billing:
                            billing_address.default = True
                            billing_address.save()

                    else:
                        messages.info(
                            self.request, "Please fill in the required billing address fields")

                payment_option = form.cleaned_data.get('payment_option')

                if payment_option == 'S':
                    return redirect('core:payment-s')
                elif payment_option == 'P':
                    return redirect('core:payment-p')
                else:
                    messages.warning(
                        self.request, "Invalid payment option selected")
                    return redirect('core:checkout')
        except ObjectDoesNotExist:
            messages.warning(self.request, "You do not have an active order")
            return redirect("core:order-summary")


class PaymentViewStripe(View):
    def get(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        if order.billing_address:
            context = {
                'order': order,
                'DISPLAY_COUPON_FORM': False
            }
            return render(self.request, "payment.html", context)
        else:
            messages.warning(
                self.request, "You have not added a billing address")
            return redirect("core:checkout")

    def post(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        token = self.request.POST.get('stripeToken')
        amount = int(order.get_total() * 100)

        try:
            charge = stripe.Charge.create(
                amount=amount,  # cents
                currency="usd",
                source=token
            )

            # create the payment
            payment = Payment()
            payment.stripe_charge_id = charge['id']
            payment.user = self.request.user
            payment.amount = order.get_total()
            payment.save()

            # assign the payment to the order

            order_items = order.items.all()
            order_items.update(ordered=True)
            for item in order_items:
                item.save()
            order.ref_code = unique_code_generator()
            order.ordered = True
            order.payment = payment
            order.save()

            messages.success(self.request, "Your order was successful!")
            return redirect("/")

        except stripe.error.CardError as e:
            body = e.json_body
            err = body.get('error', {})
            messages.warning(self.request, f"{err.get('message')}")
            return redirect("/")

        except stripe.error.RateLimitError as e:
            # Too many requests made to the API too quickly
            messages.warning(self.request, "Rate limit error")
            return redirect("/")

        except stripe.error.InvalidRequestError as e:
            # Invalid parameters were supplied to Stripe's API
            bodys = e.json_body
            errs = bodys.get('error', {})
            messages.warning(self.request, f"{errs.get('message')}")
            return redirect("/")

        except stripe.error.AuthenticationError as e:
            # Authentication with Stripe's API failed
            # (maybe you changed API keys recently)
            messages.warning(self.request, "Not authenticated")
            return redirect("/")

        except stripe.error.APIConnectionError as e:
            # Network communication with Stripe failed
            messages.warning(self.request, "Network error")
            return redirect("/")

        except stripe.error.StripeError as e:
            # Display a very generic error to the user, and maybe send
            # yourself an email
            messages.warning(
                self.request, "Something went wrong. You were not charged. Please try again.")
            return redirect("/")

        except Exception as e:
            # send an email to ourselves
            messages.warning(
                self.request, "A serious error occurred. We have been notifed.")
            return redirect("/")


class PaymentViewPaypal(View):
    def get(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        client_token = generate_client_token()
        if order.billing_address:
            context = {
                'order': order,
                'DISPLAY_COUPON_FORM': False,
                'client_token': client_token
            }
            return render(self.request, "paymentbt.html", context)
        else:
            messages.warning(
                self.request, "You have not added a billing address")
            return redirect("core:checkout")

    def post(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        amount = int(order.get_total() * 100)
        result = transact({
            'amount': amount,
            'payment_method_nonce': self.request.POST['payment_method_nonce'],
            'options': {
                "submit_for_settlement": True
            }
        })
        if result.is_success or result.transaction:
            # create the payment
            payment = Payment()
            payment.stripe_charge_id = result.transaction.id
            payment.user = self.request.user
            payment.amount = order.get_total()
            payment.save()

            # assign the payment to the order

            order_items = order.items.all()
            order_items.update(ordered=True)
            for item in order_items:
                item.save()
            order.ref_code = unique_code_generator()
            order.ordered = True
            order.payment = payment
            order.save()

            messages.success(self.request, "Your order was successful!")
            return redirect("/")
        else:
            for x in result.errors.deep_errors:
                messages.info(self.request, x)
            return redirect("/")


def HomeView(request):
    if request.method == 'POST':
        sortype = request.POST['sort']
        if (sortype=="lh"):
            item_list = Item.objects.all().order_by('discount_price')
        elif (sortype=="hl"):
            item_list = Item.objects.all().order_by('-discount_price')
    else:
        item_list = Item.objects.all()
    paginator = Paginator(item_list, 8)
    page = request.GET.get('page')
    items = paginator.get_page(page)
    context = {"items": items,
               }
    return render(request, "home.html", context)


def orderview(request):
    try:
        orders = Order.objects.filter(user = request.user, ordered = True)
        context = {"orders": orders,
                   }
        return render(request, "new.html", context)
    except ObjectDoesNotExist:
        return redirect("core:home")


def cateView(request,pk):
    cat_num = pk
    if(pk==1):
        if request.method == 'POST':
            sortype = request.POST['sort']
            if (sortype == "lh"):
                item_list = Item.objects.filter(category="Bk").order_by('price')
            elif (sortype == "hl"):
                item_list = Item.objects.filter(category="Bk").order_by('-price')
        else:
            item_list = Item.objects.filter(category="Bk")

    elif (pk == 2):
        if request.method == 'POST':
            sortype = request.POST['sort']
            if (sortype == "lh"):
                item_list = Item.objects.filter(category="Mi").order_by('price')
            elif (sortype == "hl"):
                item_list = Item.objects.filter(category="Mi").order_by('-price')
        else:
            item_list = Item.objects.filter(category="Mi")

    elif (pk == 3):
        if request.method == 'POST':
            sortype = request.POST['sort']
            if (sortype == "lh"):
                item_list = Item.objects.filter(category="St").order_by('price')
            elif (sortype == "hl"):
                item_list = Item.objects.filter(category="St").order_by('-price')
        else:
            item_list = Item.objects.filter(category="St")

    else:
        if request.method == 'POST':
            sortype = request.POST['sort']
            if (sortype == "lh"):
                item_list = Item.objects.all().order_by('discount_price')
            elif (sortype == "hl"):
                item_list = Item.objects.all().order_by('-discount_price')
        else:
            item_list = Item.objects.all()
    paginator = Paginator(item_list, 8)
    page = request.GET.get('page')
    items = paginator.get_page(page)
    context = {"items": items,
               "pk" : cat_num, }
    return render(request, "cate_home.html", context)


def search(request):
    if request.method == 'POST':
        srch = request.POST['srh']
        print(srch)
        if srch:
            match = Item.objects.filter(Q(title__icontains=srch) |
                                          Q(description__icontains=srch)
                                          )
            if match:
                return render(request, 'home.html', {"items": match,})
            else:
                messages.error(request, 'no result found')
                return HttpResponse("Nahi h esa kuch")
                #return render(request, 'products/search.html', {'sr': match})
        else:
            return redirect("core:home")


class OrderSummaryView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            context = {
                'object': order
            }
            return render(self.request, 'order_summary.html', context)
        except ObjectDoesNotExist:
            messages.warning(self.request, "You do not have an active order")
            return redirect("/")


def ItemDetailView(request, slug):
    item = get_object_or_404(Item, slug=slug)
    cate = item.category
    rel_items = []
    all_rel_items = Item.objects.filter(category = cate)
    if all_rel_items.count()<3:
        for i in range(all_rel_items.count()):
            a = all_rel_items[i]
            if not a == item:
                rel_items.append(a)
    else:
        for i in range(3):
           a = all_rel_items[i]
           if not a==item:
              rel_items.append(a)
    context = {"object": item,
               "rel_items" : rel_items,}
    return render(request, "product.html", context)



@login_required
def add_to_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_item, created = OrderItem.objects.get_or_create(
        item=item,
        user=request.user,
        ordered=False
    )
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item.quantity += 1
            order_item.save()
            messages.info(request, "This item quantity was updated.")
            return redirect("core:order-summary")
        else:
            order.items.add(order_item)
            messages.info(request, "This item was added to your cart.")
            return redirect("core:order-summary")
    else:
        ordered_date = timezone.now()
        order = Order.objects.create(
            user=request.user, ordered_date=ordered_date)
        order.items.add(order_item)
        messages.info(request, "This item was added to your cart.")
        return redirect("core:order-summary")


@login_required
def remove_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(
        user=request.user,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            order.items.remove(order_item)
            messages.info(request, "This item was removed from your cart.")
            return redirect("core:order-summary")
        else:
            messages.info(request, "This item was not in your cart")
            return redirect("core:product", slug=slug)
    else:
        messages.info(request, "You do not have an active order")
        return redirect("core:product", slug=slug)


@login_required
def remove_single_item_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(
        user=request.user,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            if order_item.quantity > 1:
                order_item.quantity -= 1
                order_item.save()
            else:
                order.items.remove(order_item)
            messages.info(request, "This item quantity was updated.")
            return redirect("core:order-summary")
        else:
            messages.info(request, "This item was not in your cart")
            return redirect("core:product", slug=slug)
    else:
        messages.info(request, "You do not have an active order")
        return redirect("core:product", slug=slug)


class AddCouponView(View):
    def post(self, *args, **kwargs):
        form = CouponForm(self.request.POST or None)
        if form.is_valid():
            qs = Order.objects.filter(
                user=self.request.user, ordered=False)
            if(qs.count()==1):
                code = form.cleaned_data.get('code')
                order = Order.objects.get(
                    user=self.request.user, ordered=False)
                coops = Coupon.objects.filter(code=code)
                if(coops.count()==1):
                    order.coupon = Coupon.objects.get(code=code)
                    order.save()
                    messages.success(self.request, "Successfully added coupon")
                    return redirect("core:checkout")
                else:
                    messages.info(self.request, "This coupon does not exist")
                    return redirect("core:checkout")
            else:
                messages.info(self.request, "You do not have an active order")
                return redirect("core:checkout")



def requestRefundView(request, pk):
    form = RefundForm()
    order = Order.objects.get(id=pk)
    if request.method == "POST":
        form = RefundForm(request.POST)
        if form.is_valid():
            order.refund_requested = True
            order.save()
            refund = Refund()
            refund.order = order
            refund.reason = form.cleaned_data.get('reason')
            refund.email = form.cleaned_data.get('email')
            refund.save()
            messages.info(request, "Your request was received.")
            return redirect("core:home")
    context = {
        'form': form
    }
    return render(request, "request_refund.html", context)