from typing import Any


def _parse_date_range(date_range: dict[str, Any] | None) -> dict[str, Any] | None:
    if not date_range:
        return None
    start = date_range.get("start") or {}
    end = date_range.get("end") or {}
    return {
        "start_year": start.get("year"),
        "start_month": start.get("month"),
        "end_year": end.get("year"),
        "end_month": end.get("month"),
        "is_current": end.get("year") is None and end.get("month") is None,
    }


def _build_image_url(entity: dict[str, Any]) -> str | None:
    """Build image URL from PhotoFilterPicture entity."""
    root_url = entity.get("rootUrl") or entity.get("root_url")
    if not root_url:
        return None

    artifacts = entity.get("artifacts") or []
    if not artifacts:
        return None

    # Pick largest artifact by width
    best = max(artifacts, key=lambda a: a.get("width", 0))
    segment = best.get("fileIdentifyingUrlPathSegment") or best.get(
        "file_identifying_url_path_segment"
    )
    if not segment:
        return None
    return f"{root_url}{segment}"


def _parse_location(profile: dict[str, Any]) -> dict[str, Any] | None:
    geo = profile.get("geoLocation") or profile.get("geoLocationName")
    if isinstance(geo, str):
        return {"display": geo}

    if isinstance(geo, dict):
        return {
            "city": geo.get("city"),
            "state": geo.get("state"),
            "country": geo.get("country"),
            "display": geo.get("defaultLocalizedName")
            or geo.get("defaultLocalizedNameWithoutCountryName"),
        }

    location_name = profile.get("locationName")
    if location_name:
        return {"display": location_name}
    return None


def _entity_type(entity: dict[str, Any]) -> str:
    return entity.get("$type") or entity.get("type") or ""


def _is_type(entity: dict[str, Any], *suffixes: str) -> bool:
    t = _entity_type(entity)
    return any(t.endswith(s) for s in suffixes)


def parse_profile_response(raw: dict[str, Any]) -> dict[str, Any]:
    """Denormalize Voyager included[] payload into ProfileResponse dict."""
    included = raw.get("included") or []

    profiles = [e for e in included if _is_type(e, "Profile")]
    profile = profiles[0] if profiles else {}

    # Fallback: try data.elements
    if not profile:
        data = raw.get("data") or {}
        elements = data.get("elements") or data.get("*elements") or []
        if elements and isinstance(elements[0], str):
            urn = elements[0]
            profile = next((e for e in included if e.get("entityUrn") == urn), {})
        elif elements and isinstance(elements[0], dict):
            profile = elements[0]

    pictures = [e for e in included if _is_type(e, "PhotoFilterPicture")]
    profile_pic_url: str | None = None
    cover_pic_url: str | None = None

    for pic in pictures:
        url = _build_image_url(pic)
        if not url:
            continue
        display_image = pic.get("displayImageReference") or pic.get("displayImageUrn")
        if display_image and "background" in str(display_image).lower():
            cover_pic_url = url
        elif profile_pic_url is None:
            profile_pic_url = url
        elif cover_pic_url is None:
            cover_pic_url = url

    # Match profile picture via profilePicture URN
    profile_pic_urn = profile.get("profilePicture") or profile.get("*profilePicture")
    if profile_pic_urn:
        for pic in pictures:
            if pic.get("entityUrn") == profile_pic_urn or pic.get("urn") == profile_pic_urn:
                profile_pic_url = _build_image_url(pic) or profile_pic_url
                break

    positions = []
    for entity in included:
        if not _is_type(entity, "Position"):
            continue
        company = entity.get("companyName") or entity.get("company", {}).get("name")
        positions.append(
            {
                "title": entity.get("title"),
                "company_name": company if isinstance(company, str) else None,
                "location": entity.get("locationName"),
                "description": entity.get("description"),
                "date_range": _parse_date_range(
                    entity.get("dateRange") or entity.get("timePeriod")
                ),
            }
        )

    educations = []
    for entity in included:
        if not _is_type(entity, "Education"):
            continue
        educations.append(
            {
                "school_name": entity.get("schoolName") or entity.get("school", {}).get("name"),
                "degree_name": entity.get("degreeName"),
                "field_of_study": entity.get("fieldOfStudy"),
                "grade": entity.get("grade"),
                "activities": entity.get("activities"),
                "date_range": _parse_date_range(
                    entity.get("dateRange") or entity.get("timePeriod")
                ),
            }
        )

    skills = []
    for entity in included:
        if not _is_type(entity, "Skill"):
            continue
        name = entity.get("name")
        if name:
            skills.append({"name": name})

    certifications = []
    for entity in included:
        if not _is_type(entity, "Certification"):
            continue
        issue = entity.get("timePeriod") or {}
        start = issue.get("start") or {}
        issue_date = None
        if start.get("year"):
            month = start.get("month", 1)
            issue_date = f"{start['year']}-{month:02d}"

        certifications.append(
            {
                "name": entity.get("name"),
                "authority": entity.get("authority"),
                "url": entity.get("url"),
                "issue_date": issue_date,
            }
        )

    languages = []
    for entity in included:
        if not _is_type(entity, "Language"):
            continue
        proficiency = entity.get("proficiency")
        if isinstance(proficiency, dict):
            proficiency = proficiency.get("name") or proficiency.get("localizedName")
        languages.append(
            {
                "name": entity.get("name"),
                "proficiency": proficiency,
            }
        )

    public_id = profile.get("publicIdentifier")
    return {
        "first_name": profile.get("firstName"),
        "last_name": profile.get("lastName"),
        "headline": profile.get("headline"),
        "summary": profile.get("summary"),
        "public_identifier": public_id,
        "profile_url": f"https://www.linkedin.com/in/{public_id}/" if public_id else None,
        "urn": profile.get("entityUrn") or profile.get("objectUrn"),
        "location": _parse_location(profile),
        "profile_picture_url": profile_pic_url,
        "cover_picture_url": cover_pic_url,
        "positions": positions,
        "educations": educations,
        "skills": skills,
        "certifications": certifications,
        "languages": languages,
    }
