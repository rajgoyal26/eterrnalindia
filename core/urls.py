from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from .views import (
    ItemDetailView,
    CheckoutView,
    HomeView,
    cateView,
    OrderSummaryView,
    add_to_cart,
    remove_from_cart,
    remove_single_item_from_cart,
    PaymentViewStripe,
    PaymentViewPaypal,
    AddCouponView,
    orderview,
    requestRefundView,
    search,
)

app_name = 'core'

urlpatterns = [
    path('', HomeView, name='home'),
    path('<int:pk>/', cateView, name='cate'),
    path('search/', search, name='item-search'),
    path('my-orders/', orderview, name='my-orders'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('order-summary/', OrderSummaryView.as_view(), name='order-summary'),
    path('product/<slug>/', ItemDetailView, name='product'),
    path('add-to-cart/<slug>/', add_to_cart, name='add-to-cart'),
    path('add-coupon/', AddCouponView.as_view(), name='add-coupon'),
    path('remove-from-cart/<slug>/', remove_from_cart, name='remove-from-cart'),
    path('remove-item-from-cart/<slug>/', remove_single_item_from_cart,
         name='remove-single-item-from-cart'),
    path('payment/stripe/', PaymentViewStripe.as_view(), name='payment-s'),
    path('payment/paypal/', PaymentViewPaypal.as_view(), name='payment-p'),
    path('request-refund/<int:pk>/', requestRefundView, name='request-refund')
]


if settings.DEBUG:
    urlpatterns = urlpatterns + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns = urlpatterns + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)