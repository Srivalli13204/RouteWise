from django.contrib import admin
from .models import TrafficIncident, ParkingLocation, RouteSearch

# Register your models here.
@admin.register(TrafficIncident)
class TrafficIncidentAdmin(admin.ModelAdmin):
    list_display = (
        "location",
        "incident_type",
        "severity",
        "is_active",
        "created_at",
    )

    list_filter = (
        "incident_type",
        "severity",
        "is_active",
    )

    search_fields = (
        "location",
        "description",
    )


@admin.register(ParkingLocation)
class ParkingLocationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "location",
        "total_slots",
        "available_slots",
        "price_per_hour",
    )

    search_fields = (
        "name",
        "location",
    )


@admin.register(RouteSearch)
class RouteSearchAdmin(admin.ModelAdmin):
    list_display = (
        "source",
        "destination",
        "distance_km",
        "estimated_time_minutes",
        "estimated_cost",
        "traffic_level",
        "created_at",
    )

    search_fields = (
        "source",
        "destination",
    )