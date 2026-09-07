def create_dive(officer_client, payload):
    response = officer_client.post(
        "/api/officer/dives", json=payload, headers={"Origin": "http://testserver"}
    )
    assert response.status_code == 201, response.text
    return response.json()


def signup(client, public_id, email):
    return client.post(
        f"/api/public/dives/{public_id}/signups",
        json={
            "name": "Test Diver",
            "email": email,
            "needs_carpool": True,
            "pickup_location": "Downtown",
            "needs_gear": True,
            "suit_size": "M",
            "shoe_size": 9.5,
        },
    )


def test_capacity_sends_later_signup_to_waitlist(client, officer_client, dive_payload):
    dive = create_dive(officer_client, dive_payload)

    first = signup(client, dive["public_id"], "FIRST@example.com")
    second = signup(client, dive["public_id"], "second@example.com")

    assert first.status_code == 201
    assert first.json()["status"] == "confirmed"
    assert second.json() == {
        "id": second.json()["id"],
        "status": "waitlisted",
        "waitlist_position": 1,
    }


def test_duplicate_email_is_rejected_case_insensitively(client, officer_client, dive_payload):
    dive = create_dive(officer_client, dive_payload)
    assert signup(client, dive["public_id"], "diver@example.com").status_code == 201

    duplicate = signup(client, dive["public_id"], "DIVER@example.com")

    assert duplicate.status_code == 409
    assert "already signed up" in duplicate.json()["detail"]


def test_rental_and_carpool_details_are_conditional(client, officer_client, dive_payload):
    dive = create_dive(officer_client, dive_payload)

    invalid = client.post(
        f"/api/public/dives/{dive['public_id']}/signups",
        json={
            "name": "Test Diver",
            "email": "test@example.com",
            "needs_carpool": True,
            "needs_gear": True,
        },
    )

    assert invalid.status_code == 422


def test_public_dive_never_exposes_roster(client, officer_client, dive_payload):
    dive = create_dive(officer_client, dive_payload)
    signup(client, dive["public_id"], "private@example.com")

    response = client.get(f"/api/public/dives/{dive['public_id']}")

    assert response.status_code == 200
    assert "private@example.com" not in response.text
    assert set(response.json()) == {
        "public_id",
        "title",
        "description",
        "location",
        "starts_at",
        "capacity",
        "remaining",
        "next_status",
    }
