import math
import time
import requests

from django.http import JsonResponse
from django.shortcuts import render

from .models import TrafficIncident, ParkingLocation, RouteSearch


def home(request):
    incidents = TrafficIncident.objects.filter(is_active=True)

    context = {
        "incidents": incidents,
    }

    return render(request, "mobility/home.html", context)


def geocode_place(place):
    """
    Convert a place name into latitude and longitude
    using the Nominatim geocoding service.
    """

    url = "https://nominatim.openstreetmap.org/search"

    params = {
        "q": place,
        "format": "json",
        "limit": 1,
    }

    headers = {
        "User-Agent": "RouteWise/1.0"
    }

    response = requests.get(
        url,
        params=params,
        headers=headers,
        timeout=10,
    )

    response.raise_for_status()

    results = response.json()

    if not results:
        return None

    return {
        "latitude": float(results[0]["lat"]),
        "longitude": float(results[0]["lon"]),
    }


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two geographic coordinates
    using the Haversine formula.

    Returns distance in kilometers.
    """

    earth_radius = 6371

    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(delta_lon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return earth_radius * c


def get_route_traffic(route_coordinates):
    """
    Check whether registered traffic incidents
    are close to the route.
    """

    incidents = TrafficIncident.objects.filter(
        is_active=True
    )

    nearby_incidents = []

    # Sample route points to reduce calculations
    sampled_points = route_coordinates[::10]

    for incident in incidents:

        closest_distance = float("inf")

        for point in sampled_points:

            route_lon = point[0]
            route_lat = point[1]

            distance = calculate_distance(
                float(incident.latitude),
                float(incident.longitude),
                route_lat,
                route_lon,
            )

            closest_distance = min(
                closest_distance,
                distance,
            )

        # Consider an incident relevant
        # if it is within 1.5 km of the route.
        if closest_distance <= 1.5:
            nearby_incidents.append(incident)

    severity_score = 0

    for incident in nearby_incidents:

        if incident.severity == "high":
            severity_score += 3

        elif incident.severity == "medium":
            severity_score += 2

        else:
            severity_score += 1

    if severity_score >= 5:
        traffic_level = "High"

    elif severity_score >= 2:
        traffic_level = "Moderate"

    else:
        traffic_level = "Low"

    return traffic_level, nearby_incidents


def get_nearby_parking(
    destination_lat,
    destination_lon,
    radius_km=3
):
    """
    Find parking locations within the specified
    radius of the destination.

    Parking is sorted by distance from destination.
    """

    nearby_parking = []

    parking_locations = ParkingLocation.objects.all()

    for parking in parking_locations:

        parking_lat = float(parking.latitude)
        parking_lon = float(parking.longitude)

        distance_from_destination = calculate_distance(
            destination_lat,
            destination_lon,
            parking_lat,
            parking_lon,
        )

        # Only include parking within the radius.
        if distance_from_destination <= radius_km:

            if parking.total_slots > 0:

                availability_percent = (
                    float(parking.available_slots)
                    / float(parking.total_slots)
                ) * 100

            else:
                availability_percent = 0

            nearby_parking.append(
                {
                    "name": parking.name,
                    "location": parking.location,
                    "available_slots": parking.available_slots,
                    "total_slots": parking.total_slots,
                    "price_per_hour": float(
                        parking.price_per_hour
                    ),
                    "latitude": parking_lat,
                    "longitude": parking_lon,
                    "distance_km": round(
                        distance_from_destination,
                        2,
                    ),
                    "availability_percent": round(
                        availability_percent
                    ),
                }
            )

    # Closest parking first.
    nearby_parking.sort(
        key=lambda parking: parking["distance_km"]
    )

    return nearby_parking

def create_waypoint(lat1, lon1, lat2, lon2, fraction, offset_km):
    """
    Creates a point near the straight line between source
    and destination, shifted sideways by offset_km.
    """

    mid_lat = lat1 + (lat2 - lat1) * fraction
    mid_lon = lon1 + (lon2 - lon1) * fraction

    # Direction of source -> destination
    dlat = lat2 - lat1
    dlon = (
        (lon2 - lon1)
        * math.cos(math.radians(mid_lat))
    )

    angle = math.atan2(dlat, dlon)

    # Perpendicular direction
    perpendicular = angle + (math.pi / 2)

    earth_radius = 6371

    offset_lat = (
        offset_km / earth_radius
    ) * math.cos(perpendicular)

    offset_lon = (
        (offset_km / earth_radius)
        * math.sin(perpendicular)
        / math.cos(math.radians(mid_lat))
    )

    waypoint_lat = mid_lat + math.degrees(offset_lat)
    waypoint_lon = mid_lon + math.degrees(offset_lon)

    return waypoint_lat, waypoint_lon


def get_osrm_route(coordinates):
    """
    Requests one route from OSRM.
    """

    url = (
        "https://router.project-osrm.org/"
        f"route/v1/driving/{coordinates}"
    )

    params = {
        "alternatives": "false",
        "geometries": "geojson",
        "overview": "full",
    }

    response = requests.get(
        url,
        params=params,
        timeout=15,
    )

    response.raise_for_status()

    data = response.json()

    if data.get("code") != "Ok":
        return None

    routes = data.get("routes", [])

    if not routes:
        return None

    return routes[0]


def is_similar_route(route1, route2):
    """
    Checks whether two route geometries are essentially the same.
    """

    geometry1 = route1["geometry"]["coordinates"]
    geometry2 = route2["geometry"]["coordinates"]

    if not geometry1 or not geometry2:
        return True

    # Compare a few points from both routes.
    positions = [0.25, 0.50, 0.75]

    for position in positions:

        index1 = int(
            len(geometry1) * position
        )

        index2 = int(
            len(geometry2) * position
        )

        index1 = min(
            index1,
            len(geometry1) - 1
        )

        index2 = min(
            index2,
            len(geometry2) - 1
        )

        lon1, lat1 = geometry1[index1]
        lon2, lat2 = geometry2[index2]

        distance = calculate_distance(
            lat1,
            lon1,
            lat2,
            lon2,
        )

        # If all checked points are very close,
        # treat the routes as the same.
        if distance > 1.0:
            return False

    return True

def route_search(request):

    if request.method != "GET":
        return JsonResponse(
            {"error": "Only GET requests are allowed."},
            status=405,
        )

    source = request.GET.get("source", "").strip()
    destination = request.GET.get("destination", "").strip()

    if not source or not destination:
        return JsonResponse(
            {"error": "Source and destination are required."},
            status=400,
        )

    try:
        # ---------------------------------------------------------
        # 1. Convert source and destination names into coordinates
        # ---------------------------------------------------------
        source_location = geocode_place(source)

        time.sleep(1)

        destination_location = geocode_place(destination)

        if not source_location:
            return JsonResponse(
                {"error": "Source location could not be found."},
                status=404,
            )

        if not destination_location:
            return JsonResponse(
                {"error": "Destination location could not be found."},
                status=404,
            )

        source_lon = source_location["longitude"]
        source_lat = source_location["latitude"]

        destination_lon = destination_location["longitude"]
        destination_lat = destination_location["latitude"]

        # ---------------------------------------------------------
        # 2. Ask OSRM for available alternative routes
        # ---------------------------------------------------------
        coordinates = (
            f"{source_lon},{source_lat};"
            f"{destination_lon},{destination_lat}"
        )

        osrm_url = (
            "https://router.project-osrm.org/"
            f"route/v1/driving/{coordinates}"
        )

        params = {
            "alternatives": "true",
            "geometries": "geojson",
            "overview": "full",
        }

        route_response = requests.get(
            osrm_url,
            params=params,
            timeout=15,
        )

        route_response.raise_for_status()

        route_data = route_response.json()

        if route_data.get("code") != "Ok":
            return JsonResponse(
                {"error": "No route could be found."},
                status=404,
            )

        available_routes = route_data.get("routes", [])

                # ---------------------------------------------------------
        # If OSRM gives only one route, try to discover
        # additional genuine routes using waypoints.
        # ---------------------------------------------------------

        if len(available_routes) < 3:

            straight_distance = calculate_distance(
                source_lat,
                source_lon,
                destination_lat,
                destination_lon,
            )

            # Keep the detour reasonable.
            offset_km = min(
                max(straight_distance * 0.08, 2),
                15,
            )

            waypoint_candidates = []

            # Try points on both sides of the direct path.
            for fraction in [0.35, 0.50, 0.65]:

                for direction in [1, -1]:

                    waypoint = create_waypoint(
                        source_lat,
                        source_lon,
                        destination_lat,
                        destination_lon,
                        fraction,
                        offset_km * direction,
                    )

                    waypoint_candidates.append(
                        waypoint
                    )

            for waypoint_lat, waypoint_lon in waypoint_candidates:

                if len(available_routes) >= 3:
                    break

                waypoint_coordinates = (
                    f"{source_lon},{source_lat};"
                    f"{waypoint_lon},{waypoint_lat};"
                    f"{destination_lon},{destination_lat}"
                )

                try:

                    alternative_route = get_osrm_route(
                        waypoint_coordinates
                    )

                    if alternative_route is None:
                        continue

                    # Don't add the route if it is basically
                    # the same path we already have.
                    duplicate = False

                    for existing_route in available_routes:

                        if is_similar_route(
                            existing_route,
                            alternative_route
                        ):
                            duplicate = True
                            break

                    if not duplicate:
                        available_routes.append(
                            alternative_route
                        )

                except requests.RequestException:
                    continue

        # ---------------------------------------------------------
        # 3. Process whatever routes OSRM actually provides
        # ---------------------------------------------------------
        routes = []

        for index, route in enumerate(available_routes):

            distance_km = route["distance"] / 1000
            time_minutes = route["duration"] / 60

            geometry = route["geometry"]["coordinates"]

            # Check traffic incidents near this route
            traffic_level, incidents = get_route_traffic(
                geometry
            )

            # RouteWise estimated travel cost
            estimated_cost = 40 + (distance_km * 12)

            # Traffic penalty used by RouteWise
            traffic_penalty = {
                "Low": 0,
                "Moderate": 8,
                "High": 18,
            }[traffic_level]

            # RouteWise comparison score
            route_score = (
                time_minutes
                + (distance_km * 1.5)
                + traffic_penalty
            )

            routes.append(
                {
                    "route_number": index + 1,
                    "distance_km": round(distance_km, 2),
                    "time_minutes": round(time_minutes),
                    "estimated_cost": round(estimated_cost),
                    "traffic_level": traffic_level,
                    "traffic_incidents": len(incidents),
                    "score": round(route_score, 2),
                    "geometry": geometry,
                }
            )

        # ---------------------------------------------------------
        # 4. Safety check
        # ---------------------------------------------------------
        if not routes:
            return JsonResponse(
                {"error": "No route could be found."},
                status=404,
            )

        # ---------------------------------------------------------
        # 5. If there is only ONE route
        #    → simply show that route
        # ---------------------------------------------------------
        if len(routes) == 1:

            routes[0]["recommended"] = True
            routes[0]["route_type"] = "Only Available Route"

        # ---------------------------------------------------------
        # 6. If there are MULTIPLE routes
        #    → compare them and recommend the best
        # ---------------------------------------------------------
        else:

            routes.sort(
                key=lambda route: route["score"]
            )

            for index, route in enumerate(routes):

                route["route_number"] = index + 1

                route["recommended"] = False
                route["route_type"] = "Alternative Route"

            # Lowest RouteWise score = recommended
            routes[0]["recommended"] = True
            routes[0]["route_type"] = "Recommended Route"

        # ---------------------------------------------------------
        # 7. Get parking near destination
        # ---------------------------------------------------------
        nearby_parking = get_nearby_parking(
            destination_lat,
            destination_lon,
            radius_km=3,
        )

        # ---------------------------------------------------------
        # 8. Save recommended/selected route in database
        # ---------------------------------------------------------
        recommended = routes[0]

        RouteSearch.objects.create(
            source=source,
            destination=destination,
            distance_km=recommended["distance_km"],
            estimated_time_minutes=recommended["time_minutes"],
            estimated_cost=recommended["estimated_cost"],
            traffic_level=recommended["traffic_level"],
        )

        # ---------------------------------------------------------
        # 9. Send result to frontend
        # ---------------------------------------------------------
        return JsonResponse(
            {
                "source": source,
                "destination": destination,
                "route_count": len(routes),
                "multiple_routes": len(routes) > 1,
                "routes": routes,
                "parking": nearby_parking,
            }
        )

    except requests.RequestException:
        return JsonResponse(
            {
                "error": (
                    "Unable to connect to the map/routing service."
                )
            },
            status=503,
        )

    except Exception as error:
        return JsonResponse(
            {"error": str(error)},
            status=500,
        )