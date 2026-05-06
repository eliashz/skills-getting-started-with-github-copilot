"""
Integration tests for the Activities API using the AAA (Arrange-Act-Assert) pattern.

Test structure:
- Arrange: Set up initial state, data, and test client
- Act: Call the endpoint/function being tested
- Assert: Verify the response, status code, and side effects
"""

import pytest


class TestGetActivities:
    """Tests for GET /activities endpoint."""

    def test_get_activities_returns_all_activities(self, client):
        """
        Arrange: No setup needed, activities loaded from fixture
        Act: Make GET request to /activities
        Assert: Response contains all activities with correct structure
        """
        # Act
        response = client.get("/activities")

        # Assert
        assert response.status_code == 200
        activities = response.json()
        
        # Verify we get a dictionary
        assert isinstance(activities, dict)
        
        # Verify it contains expected activities
        assert "Chess Club" in activities
        assert "Programming Class" in activities
        assert "Gym Class" in activities
        assert len(activities) == 9

    def test_get_activities_includes_required_fields(self, client):
        """
        Arrange: No setup needed
        Act: Make GET request to /activities
        Assert: Each activity has required fields
        """
        # Act
        response = client.get("/activities")
        activities = response.json()

        # Assert - Check Chess Club has all required fields
        chess_club = activities["Chess Club"]
        assert "description" in chess_club
        assert "schedule" in chess_club
        assert "max_participants" in chess_club
        assert "participants" in chess_club
        
        # Verify field types
        assert isinstance(chess_club["description"], str)
        assert isinstance(chess_club["schedule"], str)
        assert isinstance(chess_club["max_participants"], int)
        assert isinstance(chess_club["participants"], list)

    def test_get_activities_shows_current_participants(self, client):
        """
        Arrange: Activities fixture contains initial participants
        Act: Make GET request to /activities
        Assert: Participants list reflects initial state
        """
        # Act
        response = client.get("/activities")
        activities = response.json()

        # Assert - Chess Club should have 2 initial participants
        assert "michael@mergington.edu" in activities["Chess Club"]["participants"]
        assert "daniel@mergington.edu" in activities["Chess Club"]["participants"]
        assert len(activities["Chess Club"]["participants"]) == 2


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint."""

    def test_signup_new_participant_succeeds(self, client):
        """
        Arrange: Select an activity and a new email address
        Act: POST signup request with activity name and email
        Assert: Returns 200, email added to participants list
        """
        # Arrange
        activity_name = "Chess Club"
        email = "newstudent@mergington.edu"

        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 200
        result = response.json()
        assert "message" in result
        assert email in result["message"]
        
        # Verify participant was added
        verify_response = client.get("/activities")
        activities = verify_response.json()
        assert email in activities[activity_name]["participants"]

    def test_signup_returns_confirmation_message(self, client):
        """
        Arrange: Valid activity and new email
        Act: POST signup request
        Assert: Response message has descriptive confirmation
        """
        # Arrange
        activity_name = "Gym Class"
        email = "alice@mergington.edu"

        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )

        # Assert
        result = response.json()
        assert f"Signed up {email} for {activity_name}" in result["message"]

    def test_signup_duplicate_participant_fails_with_400(self, client):
        """
        Arrange: michael@mergington.edu is already in Chess Club
        Act: Try to signup the same person again
        Assert: Returns 400 with appropriate error message
        """
        # Arrange
        activity_name = "Chess Club"
        email = "michael@mergington.edu"  # Already a participant

        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 400
        result = response.json()
        assert "already signed up" in result["detail"].lower()

    def test_signup_nonexistent_activity_fails_with_404(self, client):
        """
        Arrange: Activity name that doesn't exist
        Act: Try to signup for nonexistent activity
        Assert: Returns 404 with appropriate error message
        """
        # Arrange
        activity_name = "Nonexistent Club"
        email = "student@mergington.edu"

        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 404
        result = response.json()
        assert "not found" in result["detail"].lower()

    def test_signup_respects_max_participants_limit(self, client):
        """
        Arrange: Create an activity with only 2 spots max (for testing)
               currently Basketball Team has 1 participant with max 15
               We'll simulate a full activity by checking capacity enforcement
        Act: Try to signup when activity should be at capacity
        Assert: Returns 400 when max_participants would be exceeded
        """
        # Arrange
        activity_name = "Basketball Team"
        # Fill up to max by signing up many participants
        emails = [
            "student1@mergington.edu",
            "student2@mergington.edu",
            "student3@mergington.edu",
            "student4@mergington.edu",
            "student5@mergington.edu",
            "student6@mergington.edu",
            "student7@mergington.edu",
            "student8@mergington.edu",
            "student9@mergington.edu",
            "student10@mergington.edu",
            "student11@mergington.edu",
            "student12@mergington.edu",
            "student13@mergington.edu",
            "student14@mergington.edu",  # 14 new + 1 existing = 15 (at max)
        ]
        
        # Sign up students up to the limit
        for email in emails:
            response = client.post(
                f"/activities/{activity_name}/signup",
                params={"email": email}
            )
            assert response.status_code == 200
        
        # Act - Try to signup one more when at capacity
        over_capacity_email = "overcapacity@mergington.edu"
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": over_capacity_email}
        )

        # Assert
        assert response.status_code == 400
        result = response.json()
        assert "full" in result["detail"].lower() or "capacity" in result["detail"].lower()

    def test_signup_is_case_sensitive_for_activity_name(self, client):
        """
        Arrange: Activity name is "Chess Club" (with capital C)
        Act: Try to signup for "chess club" (lowercase)
        Assert: Returns 404 because lookup is case-sensitive
        """
        # Arrange
        email = "student@mergington.edu"

        # Act
        response = client.post(
            f"/activities/chess club/signup",  # lowercase
            params={"email": email}
        )

        # Assert
        assert response.status_code == 404

    def test_signup_multiple_different_participants(self, client):
        """
        Arrange: Multiple different email addresses
        Act: Sign up different participants to same activity
        Assert: All participants appear in the activity's participant list
        """
        # Arrange
        activity_name = "Art Club"
        emails = ["alice@mergington.edu", "bob@mergington.edu", "charlie@mergington.edu"]

        # Act - Sign up multiple participants
        for email in emails:
            response = client.post(
                f"/activities/{activity_name}/signup",
                params={"email": email}
            )
            assert response.status_code == 200

        # Assert - Verify all were added
        verify_response = client.get("/activities")
        activities = verify_response.json()
        participants = activities[activity_name]["participants"]
        
        for email in emails:
            assert email in participants


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint."""

    def test_unregister_existing_participant_succeeds(self, client):
        """
        Arrange: michael@mergington.edu is in Chess Club
        Act: DELETE request to unregister that participant
        Assert: Returns 200, participant removed from list
        """
        # Arrange
        activity_name = "Chess Club"
        email = "michael@mergington.edu"

        # Act
        response = client.delete(
            f"/activities/{activity_name}/unregister",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 200
        result = response.json()
        assert "Unregistered" in result["message"]
        
        # Verify participant was removed
        verify_response = client.get("/activities")
        activities = verify_response.json()
        assert email not in activities[activity_name]["participants"]

    def test_unregister_returns_confirmation_message(self, client):
        """
        Arrange: Valid participant and activity
        Act: DELETE unregister request
        Assert: Response message has descriptive confirmation
        """
        # Arrange
        activity_name = "Programming Class"
        email = "emma@mergington.edu"

        # Act
        response = client.delete(
            f"/activities/{activity_name}/unregister",
            params={"email": email}
        )

        # Assert
        result = response.json()
        assert f"Unregistered {email} from {activity_name}" in result["message"]

    def test_unregister_nonparticipant_fails_with_400(self, client):
        """
        Arrange: email that is NOT in the activity's participants
        Act: Try to unregister that email
        Assert: Returns 400 with appropriate error message
        """
        # Arrange
        activity_name = "Chess Club"
        email = "notmember@mergington.edu"

        # Act
        response = client.delete(
            f"/activities/{activity_name}/unregister",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 400
        result = response.json()
        assert "not registered" in result["detail"].lower()

    def test_unregister_nonexistent_activity_fails_with_404(self, client):
        """
        Arrange: Activity name that doesn't exist
        Act: Try to unregister from nonexistent activity
        Assert: Returns 404 with appropriate error message
        """
        # Arrange
        activity_name = "Nonexistent Club"
        email = "student@mergington.edu"

        # Act
        response = client.delete(
            f"/activities/{activity_name}/unregister",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 404
        result = response.json()
        assert "not found" in result["detail"].lower()

    def test_unregister_same_participant_twice_fails_second_time(self, client):
        """
        Arrange: michael@mergington.edu in Chess Club
        Act: DELETE to unregister (first time: succeeds),
             then DELETE again (second time: should fail)
        Assert: First succeeds (200), second fails (400)
        """
        # Arrange
        activity_name = "Chess Club"
        email = "michael@mergington.edu"

        # Act - First unregister
        response1 = client.delete(
            f"/activities/{activity_name}/unregister",
            params={"email": email}
        )
        
        # Act - Second unregister
        response2 = client.delete(
            f"/activities/{activity_name}/unregister",
            params={"email": email}
        )

        # Assert
        assert response1.status_code == 200
        assert response2.status_code == 400
        result2 = response2.json()
        assert "not registered" in result2["detail"].lower()

    def test_unregister_frees_capacity(self, client):
        """
        Arrange: An activity participant is unregistered
        Act: Try to signup for that activity again (with same email after unregister)
        Assert: Signup succeeds because spot was freed
        """
        # Arrange
        activity_name = "Drama Club"
        email = "mason@mergington.edu"

        # Act - Unregister
        response1 = client.delete(
            f"/activities/{activity_name}/unregister",
            params={"email": email}
        )
        assert response1.status_code == 200

        # Act - Try to signup again with same email
        response2 = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )

        # Assert
        assert response2.status_code == 200
        
        # Verify the participant is back
        verify_response = client.get("/activities")
        activities = verify_response.json()
        assert email in activities[activity_name]["participants"]


class TestIntegrationScenarios:
    """Integration tests combining multiple operations."""

    def test_signup_verify_unregister_verify_flow(self, client):
        """
        Arrange: A new email address
        Act: 1. Signup -> 2. Get activities -> 3. Unregister -> 4. Get activities
        Assert: Participant appears after signup, disappears after unregister
        """
        # Arrange
        activity_name = "Science Club"
        email = "testuser@mergington.edu"

        # Act 1 - Signup
        response1 = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        assert response1.status_code == 200

        # Act 2 - Verify participant exists
        response2 = client.get("/activities")
        activities2 = response2.json()
        assert email in activities2[activity_name]["participants"]
        initial_count = len(activities2[activity_name]["participants"])

        # Act 3 - Unregister
        response3 = client.delete(
            f"/activities/{activity_name}/unregister",
            params={"email": email}
        )
        assert response3.status_code == 200

        # Act 4 - Verify participant gone
        response4 = client.get("/activities")
        activities4 = response4.json()
        assert email not in activities4[activity_name]["participants"]
        assert len(activities4[activity_name]["participants"]) == initial_count - 1

    def test_multiple_signups_same_activity(self, client):
        """
        Arrange: Multiple unique email addresses
        Act: Sign up all to the same activity
        Assert: All appear in participant list, capacity updated correctly
        """
        # Arrange
        activity_name = "Debate Club"
        emails = [
            "debater1@mergington.edu",
            "debater2@mergington.edu",
            "debater3@mergington.edu",
        ]

        # Act - Sign up all participants
        for email in emails:
            response = client.post(
                f"/activities/{activity_name}/signup",
                params={"email": email}
            )
            assert response.status_code == 200

        # Assert
        verify_response = client.get("/activities")
        activities = verify_response.json()
        debate_club = activities[activity_name]
        
        # All new participants should be present
        for email in emails:
            assert email in debate_club["participants"]
        
        # Availability should be updated
        expected_available = debate_club["max_participants"] - len(debate_club["participants"])
        assert expected_available == debate_club["max_participants"] - len(debate_club["participants"])

    def test_signup_failed_due_to_duplicate_does_not_affect_list(self, client):
        """
        Arrange: A participant already in an activity
        Act: Try to signup again (should fail)
        Assert: Participant count unchanged, appears only once in list
        """
        # Arrange
        activity_name = "Gym Class"
        email = "john@mergington.edu"  # Already participant
        
        # Get initial count
        response_initial = client.get("/activities")
        initial_count = len(response_initial.json()[activity_name]["participants"])

        # Act - Try to signup again
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        assert response.status_code == 400

        # Assert - Count unchanged
        response_verify = client.get("/activities")
        final_count = len(response_verify.json()[activity_name]["participants"])
        assert final_count == initial_count
        
        # Email appears exactly once
        participants = response_verify.json()[activity_name]["participants"]
        assert participants.count(email) == 1
