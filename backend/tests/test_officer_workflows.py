from test_public_signup import create_dive, signup

from models.entities import GearCategory, Inventory, SuitSize

ORIGIN = {"Origin": "http://testserver"}


def test_protected_routes_require_login_and_origin(client, officer_client):
    client.cookies.clear()
    assert client.get("/api/officer/dives").status_code == 401
    login = client.post("/api/auth/login", json={"password": "club-password"}, headers=ORIGIN)
    assert login.status_code == 200
    assert login.cookies.get("officer_session")
    assert client.post("/api/officer/officers", json={"name": "No Origin"}).status_code == 403


def test_only_first_waitlisted_member_can_be_promoted(officer_client, dive_payload):
    dive = create_dive(officer_client, dive_payload)
    confirmed = signup(officer_client, dive["public_id"], "confirmed@example.com").json()
    first = signup(officer_client, dive["public_id"], "first@example.com").json()
    second = signup(officer_client, dive["public_id"], "second@example.com").json()

    full = officer_client.post(f"/api/officer/signups/{first['id']}/promote", headers=ORIGIN)
    assert full.status_code == 409
    officer_client.delete(f"/api/officer/signups/{confirmed['id']}", headers=ORIGIN)
    out_of_order = officer_client.post(
        f"/api/officer/signups/{second['id']}/promote", headers=ORIGIN
    )
    assert out_of_order.status_code == 409
    promoted = officer_client.post(f"/api/officer/signups/{first['id']}/promote", headers=ORIGIN)
    assert promoted.status_code == 200
    assert promoted.json()["status"] == "confirmed"


def test_gear_and_staffing_warnings_use_confirmed_demand(db, officer_client, dive_payload):
    dive_payload["capacity"] = 2
    dive = create_dive(officer_client, dive_payload)
    db.add_all(
        [
            Inventory(category=GearCategory.wetsuit, suit_size=SuitSize.M, quantity=0),
            Inventory(category=GearCategory.fins, min_shoe_size=8, max_shoe_size=10, quantity=1),
            Inventory(category=GearCategory.mask, quantity=1),
            Inventory(category=GearCategory.weight_set, quantity=1),
        ]
    )
    db.commit()
    signup(officer_client, dive["public_id"], "one@example.com")
    signup(officer_client, dive["public_id"], "two@example.com")
    signup(officer_client, dive["public_id"], "waitlist@example.com")

    detail = officer_client.get(f"/api/officer/dives/{dive['id']}").json()

    assert "Fewer than two active officers are assigned" in detail["warnings"]
    assert "Loaner gear demand exceeds inventory" in detail["warnings"]
    masks = next(row for row in detail["gear"] if row["category"] == "mask")
    assert masks["confirmed_needed"] == 2
    assert masks["waitlisted_needed"] == 1


def test_overlapping_fin_ranges_share_demand_without_false_shortage(
    officer_client, dive_payload
):
    dive_payload["capacity"] = 2
    dive = create_dive(officer_client, dive_payload)
    inventory = [
        {"category": "wetsuit", "suit_size": "M", "quantity": 2},
        {"category": "fins", "min_shoe_size": 5, "max_shoe_size": 7, "quantity": 1},
        {"category": "fins", "min_shoe_size": 6, "max_shoe_size": 8, "quantity": 1},
        {"category": "mask", "quantity": 2},
        {"category": "weight_set", "quantity": 2},
    ]
    created = [
        officer_client.post("/api/officer/inventory", json=item, headers=ORIGIN)
        for item in inventory
    ]
    assert all(response.status_code == 201 for response in created)

    edited = officer_client.put(
        f"/api/officer/inventory/{created[2].json()['id']}",
        json={
            "category": "fins",
            "min_shoe_size": 5.5,
            "max_shoe_size": 8.5,
            "quantity": 1,
        },
        headers=ORIGIN,
    )
    assert edited.status_code == 200

    for index in range(2):
        response = officer_client.post(
            f"/api/public/dives/{dive['public_id']}/signups",
            json={
                "name": f"Fin Diver {index}",
                "email": f"fins{index}@example.com",
                "phone": f"561-555-010{index}",
                "needs_carpool": False,
                "needs_gear": True,
                "suit_size": "M",
                "shoe_size": 6.5,
            },
        )
        assert response.status_code == 201

    detail = officer_client.get(f"/api/officer/dives/{dive['id']}").json()
    fin_rows = [row for row in detail["gear"] if row["category"] == "fins"]

    assert sum(row["confirmed_needed"] for row in fin_rows) == 2
    assert not any(row["shortage"] for row in fin_rows)
    assert "Loaner gear demand exceeds inventory" not in detail["warnings"]


def test_dive_detail_includes_contact_driving_and_confirmed_ride_totals(
    officer_client, dive_payload
):
    dive_payload["capacity"] = 2
    dive = create_dive(officer_client, dive_payload)
    signup(officer_client, dive["public_id"], "rider@example.com")
    driver = officer_client.post(
        f"/api/public/dives/{dive['public_id']}/signups",
        json={
            "name": "Test Driver",
            "email": "driver@example.com",
            "phone": "561-555-0199",
            "needs_carpool": False,
            "can_drive": True,
            "available_seats": 3,
            "needs_gear": False,
        },
    )
    waitlisted_driver = officer_client.post(
        f"/api/public/dives/{dive['public_id']}/signups",
        json={
            "name": "Waitlisted Driver",
            "email": "waitlisted-driver@example.com",
            "phone": "561-555-0188",
            "needs_carpool": False,
            "can_drive": True,
            "available_seats": 4,
            "needs_gear": False,
        },
    )

    assert driver.status_code == 201
    assert waitlisted_driver.json()["status"] == "waitlisted"
    detail = officer_client.get(f"/api/officer/dives/{dive['id']}").json()

    assert detail["rides_needed"] == 1
    assert detail["seats_available"] == 3
    saved_driver = next(item for item in detail["confirmed"] if item["can_drive"])
    assert saved_driver["phone"] == "561-555-0199"
    assert saved_driver["available_seats"] == 3


def test_deleting_dive_cascades_signups(db, officer_client, dive_payload):
    from sqlalchemy import func, select

    from models.entities import Signup

    dive = create_dive(officer_client, dive_payload)
    signup(officer_client, dive["public_id"], "delete@example.com")
    response = officer_client.delete(f"/api/officer/dives/{dive['id']}", headers=ORIGIN)

    assert response.status_code == 204
    assert db.scalar(select(func.count()).select_from(Signup)) == 0
