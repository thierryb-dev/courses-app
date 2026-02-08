from django.urls import path
from . import views

urlpatterns = [
    path("", views.my_households, name="my_households"),
    path("households/create/", views.create_household, name="create_household"),
]
