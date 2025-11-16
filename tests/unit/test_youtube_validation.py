"""
test_youtube_validation.py

This module contains unit tests for the YouTube validation helpers in src.updater.
"""
# lib imports
import pytest

# local imports
from src.updater import (
    parse_youtube_duration_seconds,
    is_age_restricted,
    is_available_in_us,
    is_public,
    is_valid_duration,
    validate_youtube_requirements,
)


class TestParseYouTubeDurationSeconds:
    @pytest.mark.parametrize(
        "duration,expected",
        [
            ("PT30S", 30),
            ("PT29S", 29),
            ("PT4M13S", 253),
            ("PT5M", 300),
            ("PT1H2M3S", 3723),
            ("PT", 0),
            ("", 0),
            (None, 0),
            ("INVALID", 0),
        ],
    )
    def test_parse(self, duration, expected):
        assert parse_youtube_duration_seconds(duration) == expected


class TestIsAgeRestricted:
    def test_true(self):
        content_details = {"contentRating": {"ytRating": "ytAgeRestricted"}}
        assert is_age_restricted(content_details) is True

    def test_false_missing(self):
        assert is_age_restricted({}) is False

    def test_false_other_value(self):
        content_details = {"contentRating": {"ytRating": "ytUnrestricted"}}
        assert is_age_restricted(content_details) is False


class TestIsAvailableInUS:
    def test_worldwide_no_rr(self):
        assert is_available_in_us({}) is True

    def test_allowed_includes_us(self):
        cd = {"regionRestriction": {"allowed": ["US", "CA"]}}
        assert is_available_in_us(cd) is True

    def test_allowed_excludes_us(self):
        cd = {"regionRestriction": {"allowed": ["CA", "GB"]}}
        assert is_available_in_us(cd) is False

    def test_blocked_includes_us(self):
        cd = {"regionRestriction": {"blocked": ["US", "DE"]}}
        assert is_available_in_us(cd) is False

    def test_blocked_excludes_us(self):
        cd = {"regionRestriction": {"blocked": ["DE", "FR"]}}
        assert is_available_in_us(cd) is True

    def test_rr_present_but_empty(self):
        cd = {"regionRestriction": {}}
        assert is_available_in_us(cd) is True


class TestIsPublic:
    def test_public(self):
        status = {"privacyStatus": "public"}
        assert is_public(status) is True

    def test_private(self):
        status = {"privacyStatus": "private"}
        assert is_public(status) is False

    def test_unlisted(self):
        status = {"privacyStatus": "unlisted"}
        assert is_public(status) is False

    def test_missing(self):
        assert is_public({}) is False


class TestIsValidDuration:
    def test_too_short(self):
        content_details = {"duration": "PT10S"}
        is_valid, seconds = is_valid_duration(content_details)
        assert is_valid is False
        assert seconds == 10

    def test_too_long(self):
        content_details = {"duration": "PT6M"}
        is_valid, seconds = is_valid_duration(content_details)
        assert is_valid is False
        assert seconds == 360

    def test_min_boundary(self):
        content_details = {"duration": "PT30S"}
        is_valid, seconds = is_valid_duration(content_details)
        assert is_valid is True
        assert seconds == 30

    def test_max_boundary(self):
        content_details = {"duration": "PT5M"}
        is_valid, seconds = is_valid_duration(content_details)
        assert is_valid is True
        assert seconds == 300

    def test_valid_middle(self):
        content_details = {"duration": "PT2M30S"}
        is_valid, seconds = is_valid_duration(content_details)
        assert is_valid is True
        assert seconds == 150

    def test_custom_range(self):
        content_details = {"duration": "PT45S"}
        is_valid, seconds = is_valid_duration(content_details, min_seconds=60, max_seconds=120)
        assert is_valid is False
        assert seconds == 45


class TestValidateYouTubeRequirements:
    @staticmethod
    def make_item(
            duration: str,
            rr: dict | None = None,
            age: str | None = None,
            privacy: str = "public",
    ) -> dict:
        content = {"duration": duration}
        if rr is not None:
            content["regionRestriction"] = rr
        if age is not None:
            content["contentRating"] = {"ytRating": age}
        status = {"privacyStatus": privacy}
        return {"contentDetails": content, "status": status}

    def test_short_video(self):
        item = self.make_item("PT10S")
        errors = validate_youtube_requirements(item)
        assert len(errors) == 1
        assert "too short" in errors[0]

    def test_long_video(self):
        item = self.make_item("PT6M1S")
        errors = validate_youtube_requirements(item)
        assert len(errors) == 1
        assert "too long" in errors[0]

    def test_boundary_min_ok(self):
        item = self.make_item("PT30S")
        errors = validate_youtube_requirements(item)
        assert len(errors) == 0

    def test_boundary_max_ok(self):
        item = self.make_item("PT5M")
        errors = validate_youtube_requirements(item)
        assert len(errors) == 0

    def test_age_restricted(self):
        item = self.make_item("PT1M", age="ytAgeRestricted")
        errors = validate_youtube_requirements(item)
        assert len(errors) == 1
        assert "age-restricted" in errors[0]

    def test_not_available_in_us_allowed(self):
        item = self.make_item("PT1M", rr={"allowed": ["CA"]})
        errors = validate_youtube_requirements(item)
        assert len(errors) == 1
        assert "USA" in errors[0]

    def test_not_available_in_us_blocked(self):
        item = self.make_item("PT1M", rr={"blocked": ["US", "CA"]})
        errors = validate_youtube_requirements(item)
        assert len(errors) == 1
        assert "USA" in errors[0]

    def test_private_video(self):
        item = self.make_item("PT1M", privacy="private")
        errors = validate_youtube_requirements(item)
        assert len(errors) == 1
        assert "public" in errors[0] and "private" in errors[0]

    def test_unlisted_video(self):
        item = self.make_item("PT1M", privacy="unlisted")
        errors = validate_youtube_requirements(item)
        assert len(errors) == 1
        assert "public" in errors[0] and "unlisted" in errors[0]

    def test_multiple_errors(self):
        # Video that is too short, age-restricted, and private
        item = self.make_item("PT10S", age="ytAgeRestricted", privacy="private")
        errors = validate_youtube_requirements(item)
        assert len(errors) == 3
        assert any("too short" in e for e in errors)
        assert any("age-restricted" in e for e in errors)
        assert any("public" in e for e in errors)

    def test_success(self):
        item = self.make_item("PT2M", rr={"allowed": ["US", "CA"]})
        errors = validate_youtube_requirements(item)
        assert len(errors) == 0
