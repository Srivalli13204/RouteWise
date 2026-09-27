from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
     path(
        "api/route-search/",
        views.route_search,
        name="route_search",
    ),
]