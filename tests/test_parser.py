import json
from pathlib import Path

from app.models.profile import ProfileResponse
from app.parsers.profile_parser import parse_profile_response, skills_paging_info


FIXTURES = Path(__file__).parent / "fixtures"
ROOT = Path(__file__).resolve().parents[1]


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
    assert profile.location.country == "US"
    assert profile.location.display == "San Francisco, California, United States"
    assert profile.location.city == "San Francisco"
    assert profile.location.state == "California"

    assert profile.profile_picture_url == "https://media.licdn.com/dms/image/profile/john-doe_400"
    assert profile.cover_picture_url == "https://media.licdn.com/dms/image/background/cover_800"

    assert len(profile.positions) == 2
    assert profile.positions[0].title == "Senior Software Engineer"
    assert profile.positions[0].company_name == "Acme Corp"
    assert profile.positions[0].employment_type == "Full-time"
    assert profile.positions[0].date_range is not None
    assert profile.positions[0].date_range.start_year == 2020
    assert profile.positions[1].employment_type == "Internship"
    assert profile.positions[1].date_range is not None
    assert profile.positions[1].date_range.is_current is True

    assert len(profile.educations) == 1
    assert profile.educations[0].school_name == "State University"
    assert profile.educations[0].degree_name == "Bachelor of Science"
    assert profile.educations[0].description == "Focused on distributed systems."

    assert [s.name for s in profile.skills] == ["Python", "FastAPI"]
    assert profile.skills_total == 2

    assert len(profile.certifications) == 1
    assert profile.certifications[0].name == "AWS Solutions Architect"
    assert profile.certifications[0].issue_date == "2021-04"

    assert len(profile.languages) == 2
    assert profile.languages[0].name == "English"
    assert profile.languages[1].proficiency == "PROFESSIONAL_WORKING"

    assert len(profile.treasury_media) == 2
    assert profile.treasury_media[0].kind == "url"
    assert profile.treasury_media[0].url == "https://github.com/johndoe"
    assert profile.treasury_media[0].provider == "github.com"
    assert profile.treasury_media[1].kind == "document"
    assert profile.treasury_media[1].url == "https://media.licdn.com/dms/document/resume.pdf"
    assert profile.treasury_media[1].title == "Resume"


def test_parse_profile_response_from_file():
    path = FIXTURES / "voyager_sample.json"
    with path.open() as f:
        raw = json.load(f)
    result = parse_profile_response(raw)
    assert result["first_name"] == "John"


def test_skills_paging_info(voyager_sample):
    total, existing, profile_urn = skills_paging_info(voyager_sample)
    assert total == 2
    assert existing == 2
    assert profile_urn == "urn:li:fsd_profile:ACoAAB123456789"

    # Simulate incomplete first page
    for entity in voyager_sample["included"]:
        if entity.get("entityUrn") == "urn:li:collectionResponse:skills-page-1":
            entity["paging"]["total"] = 4
            break
    total, existing, _ = skills_paging_info(voyager_sample)
    assert total == 4
    assert existing == 2


def test_parse_real_sample_json():
    path = ROOT / "sample.json"
    if not path.exists():
        return
    with path.open() as f:
        raw = json.load(f)
    profile = ProfileResponse.model_validate(parse_profile_response(raw))

    assert profile.first_name == "Shreyan"
    assert profile.profile_picture_url is not None
    assert profile.cover_picture_url is not None
    assert profile.location is not None
    assert profile.location.country == "IN"
    assert profile.location.display and profile.location.display != "IN"
    assert profile.certifications
    assert profile.certifications[0].issue_date == "2023-06"
    assert any(e.description for e in profile.educations)
    assert any(p.employment_type for p in profile.positions)
    assert len(profile.treasury_media) == 3
    assert {t.kind for t in profile.treasury_media} == {"url", "document"}
    assert len(profile.skills) == 20  # first page only without pagination
