from django.db import models

# Create your models here.
class TrafficIncident(models.Model):

    INCIDENT_TYPES = [
        ("traffic", "Heavy Traffic"),
        ("accident", "Accident"),
        ("roadwork", "Road Work"),
        ("waterlogging", "Waterlogging"),
        ("road_damage", "Road Damage"),
    ]

    SEVERITY_LEVELS = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
    ]

    location = models.CharField(max_length=200)

    incident_type = models.CharField(
        max_length=30,
        choices=INCIDENT_TYPES
    )

    severity = models.CharField(
        max_length=10,
        choices=SEVERITY_LEVELS
    )

    description = models.TextField(blank=True)

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.location} - {self.incident_type}"


class ParkingLocation(models.Model):

    name = models.CharField(max_length=200)

    location = models.CharField(max_length=200)

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6
    )

    total_slots = models.PositiveIntegerField()

    available_slots = models.PositiveIntegerField()

    price_per_hour = models.DecimalField(
        max_digits=8,
        decimal_places=2
    )

    def __str__(self):
        return self.name


class RouteSearch(models.Model):

    source = models.CharField(max_length=200)

    destination = models.CharField(max_length=200)

    distance_km = models.DecimalField(
        max_digits=8,
        decimal_places=2
    )

    estimated_time_minutes = models.PositiveIntegerField()

    estimated_cost = models.DecimalField(
        max_digits=8,
        decimal_places=2
    )

    traffic_level = models.CharField(max_length=20)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.source} → {self.destination}"