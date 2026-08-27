import json
from pathlib import Path

from app.models.profile import ProfileResponse
from app.parsers.profile_parser import parse_profile_response


def test_parse_profile_response(voyager_sample):
    result = parse_profile_response(voyager_sample)
    profile = ProfileResponse.model_validate(result)

    assert profile.first_name == "John"
    assert profile.last_name == "Doe"
    assert profile.headline == "Software Engineer at Acme Corp"
    assert profile.summary == "Experienced engineer building scalable systems."
    assert profile.public_identifier == "john-doe"
    assert profile.profile_url == "https://www.linkedin.com/in/john-doe/"
    assert profile.location is not None
    assert profile.location.display == "San Francisco, California, United States"

    assert profile.profile_picture_url == "https://media.licdn.com/dms/image/profile/john-doe_400"
    assert profile.cover_picture_url == "https://media.licdn.com/dms/image/background/cover_800"

    assert len(profile.positions) == 2
    assert profile.positions[0].title == "Senior Software Engineer"
    assert profile.positions[0].company_name == "Acme Corp"
    assert profile.positions[0].date_range is not None
    assert profile.positions[0].date_range.start_year == 2020
    assert profile.positions[1].date_range is not None
    assert profile.positions[1].date_range.is_current is True

    assert len(profile.educations) == 1
    assert profile.educations[0].school_name == "State University"
    assert profile.educations[0].degree_name == "Bachelor of Science"

    assert [s.name for s in profile.skills] == ["Python", "FastAPI"]

    assert len(profile.certifications) == 1
    assert profile.certifications[0].name == "AWS Solutions Architect"
    assert profile.certifications[0].issue_date == "2021-04"

    assert len(profile.languages) == 2
    assert profile.languages[0].name == "English"
    assert profile.languages[1].proficiency == "PROFESSIONAL_WORKING"


def test_parse_profile_response_from_file():
    path = Path(__file__).parent / "fixtures" / "voyager_sample.json"
    with path.open() as f:
        raw = json.load(f)
    result = parse_profile_response(raw)
    assert result["first_name"] == "John"
