from django.urls import path

from . import views

app_name = "quotes"

urlpatterns = [
    path("", views.QuoteListView.as_view(), name="quote_list"),
    path("nueva/", views.QuoteEditView.as_view(), name="quote_create"),
    path("<int:pk>/", views.QuoteDetailView.as_view(), name="quote_detail"),
    path("<int:pk>/editar/", views.QuoteEditView.as_view(), name="quote_update"),
    path("<int:pk>/estado/", views.QuoteStatusView.as_view(), name="quote_status"),
    path("<int:pk>/seguimiento/", views.QuoteFollowUpView.as_view(), name="quote_follow_up"),
    path("<int:pk>/duplicar/", views.QuoteDuplicateView.as_view(), name="quote_duplicate"),
    path("<int:pk>/pdf/", views.QuotePdfView.as_view(), name="quote_pdf"),
]
