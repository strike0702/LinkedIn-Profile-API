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


def _build_image_url_from_vector(vector: dict[str, Any] | None) -> str | None:
    if not vector or not isinstance(vector, dict):
        return None
    root_url = vector.get("rootUrl") or vector.get("root_url")
    if not root_url:
        return None

    artifacts = vector.get("artifacts") or []
    if not artifacts:
        return None

    best = max(artifacts, key=lambda a: a.get("width", 0))
    segment = best.get("fileIdentifyingUrlPathSegment") or best.get(
        "file_identifying_url_path_segment"
    )
    if not segment:
        return None
    return f"{root_url}{segment}"


def _extract_vector_image(picture: dict[str, Any] | None) -> dict[str, Any] | None:
    """Pull vectorImage from nested PhotoFilterPicture / picture dict."""
    if not picture or not isinstance(picture, dict):
        return None

    # Standalone PhotoFilterPicture entity (fixture shape)
    if picture.get("rootUrl") or picture.get("artifacts"):
        return picture

    for key in (
        "displayImageReference",
        "displayImageWithFrameReferenceUnion",
        "originalImageReference",
    ):
        ref = picture.get(key)
        if isinstance(ref, dict):
            vector = ref.get("vectorImage")
            if isinstance(vector, dict) and (vector.get("rootUrl") or vector.get("artifacts")):
                return vector
    return None


def _build_image_url(entity: dict[str, Any] | None) -> str | None:
    """Build image URL from nested picture dict or PhotoFilterPicture entity."""
    return _build_image_url_from_vector(_extract_vector_image(entity))


def _geo_map(included: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        e["entityUrn"]: e
        for e in included
        if _is_type(e, "Geo") and e.get("entityUrn")
    }


def _split_geo_display(display: str | None) -> tuple[str | None, str | None, str | None]:
    """Best-effort city/state/country from 'City, State, Country' display strings."""
    if not display:
        return None, None, None
    parts = [p.strip() for p in display.split(",") if p.strip()]
    if len(parts) >= 3:
        return parts[0], parts[1], parts[-1]
    if len(parts) == 2:
        return parts[0], None, parts[1]
    if len(parts) == 1:
        return None, None, parts[0]
    return None, None, None


def _parse_location(
    profile: dict[str, Any],
    included: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    location = profile.get("location") if isinstance(profile.get("location"), dict) else {}
    country_code = location.get("countryCode") if isinstance(location, dict) else None

    location_name = profile.get("locationName")
    if location_name:
        city, state, country = _split_geo_display(location_name)
        return {
            "city": city,
            "state": state,
            "country": country_code or country,
            "display": location_name,
        }

    geo = profile.get("geoLocation") or profile.get("geoLocationName")
    if isinstance(geo, str) and geo and not geo.startswith("urn:"):
        city, state, country = _split_geo_display(geo)
        return {
            "city": city,
            "state": state,
            "country": country_code or country,
            "display": geo,
        }

    # Resolve geoUrn / *geo against included Geo entities (real Voyager shape)
    if isinstance(geo, dict):
        display = geo.get("defaultLocalizedName") or geo.get(
            "defaultLocalizedNameWithoutCountryName"
        )
        city = geo.get("city")
        state = geo.get("state")
        country = geo.get("country")

        geo_urn = geo.get("geoUrn") or geo.get("*geo") or geo.get("entityUrn")
        if included and geo_urn:
            resolved = _geo_map(included).get(geo_urn)
            if resolved:
                display = (
                    resolved.get("defaultLocalizedName")
                    or resolved.get("defaultLocalizedNameWithoutCountryName")
                    or display
                )
                without = resolved.get("defaultLocalizedNameWithoutCountryName")
                if without and (city is None or state is None):
                    c2, s2, _ = _split_geo_display(without)
                    city = city or c2
                    state = state or s2
                if display and (city is None or state is None):
                    c2, s2, country_name = _split_geo_display(display)
                    city = city or c2
                    state = state or s2
                    country = country or country_name

        if display or city or state or country or country_code:
            if display is None and country_code:
                display = country_code
            return {
                "city": city,
                "state": state,
                "country": country_code or country,
                "display": display,
            }

    if country_code:
        return {"country": country_code, "display": country_code}

    return None


def _entity_type(entity: dict[str, Any]) -> str:
    return entity.get("$type") or entity.get("type") or ""


def _is_type(entity: dict[str, Any], *suffixes: str) -> bool:
    t = _entity_type(entity)
    return any(t.endswith(s) for s in suffixes)


def _find_profile(included: list[dict[str, Any]], raw: dict[str, Any]) -> dict[str, Any]:
    data = raw.get("data") or {}
    elements = data.get("elements") or data.get("*elements") or []
    if elements and isinstance(elements[0], str):
        urn = elements[0]
        match = next((e for e in included if e.get("entityUrn") == urn), None)
        if match:
            return match
    if elements and isinstance(elements[0], dict):
        return elements[0]

    profiles = [e for e in included if _is_type(e, "Profile")]
    if profiles:
        return profiles[0]
    return {}


def _format_issue_date(entity: dict[str, Any]) -> str | None:
    date_src = entity.get("dateRange") or entity.get("timePeriod") or {}
    start = date_src.get("start") or {}
    year = start.get("year")
    if not year:
        return None
    month = start.get("month", 1)
    return f"{year}-{month:02d}"


def _parse_treasury_item(entity: dict[str, Any]) -> dict[str, Any] | None:
    data = entity.get("data") or {}
    url: str | None = None
    kind: str | None = None

    if "Url" in data:
        url = data.get("Url")
        kind = "url"
    elif "NativeDocument" in data:
        doc = data.get("NativeDocument") or {}
        url = doc.get("transcribedDocumentUrl") or doc.get("manifestUrl")
        kind = "document"
    else:
        return None

    return {
        "title": entity.get("title"),
        "url": url,
        "provider": entity.get("providerName"),
        "kind": kind,
    }


def skills_paging_info(raw: dict[str, Any]) -> tuple[int, int, str | None]:
    """Return (total, existing_skill_count, profile_urn) from a raw Voyager payload."""
    included = raw.get("included") or []
    profile = _find_profile(included, raw)
    profile_urn = profile.get("entityUrn")
    existing = sum(1 for e in included if _is_type(e, "Skill"))

    skills_ref = profile.get("*profileSkills") or profile.get("profileSkills")
    total = existing
    if skills_ref:
        for entity in included:
            if entity.get("entityUrn") == skills_ref:
                paging = entity.get("paging") or {}
                total = paging.get("total", existing)
                break

    return total, existing, profile_urn


def merge_skill_entities(raw: dict[str, Any], extra_skills: list[dict[str, Any]]) -> dict[str, Any]:
    """Append Skill entities into included[], skipping duplicate entityUrns."""
    if not extra_skills:
        return raw

    included = list(raw.get("included") or [])
    seen = {
        e.get("entityUrn")
        for e in included
        if _is_type(e, "Skill") and e.get("entityUrn")
    }
    for skill in extra_skills:
        urn = skill.get("entityUrn")
        if urn and urn in seen:
            continue
        if urn:
            seen.add(urn)
        included.append(skill)

    merged = dict(raw)
    merged["included"] = included
    return merged


def parse_profile_response(raw: dict[str, Any]) -> dict[str, Any]:
    """Denormalize Voyager included[] payload into ProfileResponse dict."""
    included = raw.get("included") or []
    profile = _find_profile(included, raw)

    # Prefer nested Profile picture fields; fall back to included PhotoFilterPicture
    profile_pic_url = _build_image_url(profile.get("profilePicture"))
    cover_pic_url = _build_image_url(profile.get("backgroundPicture"))

    if profile_pic_url is None or cover_pic_url is None:
        pictures = [e for e in included if _is_type(e, "PhotoFilterPicture")]
        profile_pic_urn = profile.get("profilePicture") or profile.get("*profilePicture")

        for pic in pictures:
            url = _build_image_url(pic)
            if not url:
                continue
            if (
                isinstance(profile_pic_urn, str)
                and (pic.get("entityUrn") == profile_pic_urn or pic.get("urn") == profile_pic_urn)
            ):
                profile_pic_url = profile_pic_url or url
                continue

            display_image = pic.get("displayImageReference") or pic.get("displayImageUrn")
            if display_image and "background" in str(display_image).lower():
                cover_pic_url = cover_pic_url or url
            elif profile_pic_url is None:
                profile_pic_url = url
            elif cover_pic_url is None:
                cover_pic_url = url

    employment_types: dict[str, str] = {}
    for entity in included:
        if not _is_type(entity, "EmploymentType"):
            continue
        urn = entity.get("entityUrn")
        name = entity.get("name")
        if urn and name:
            employment_types[urn] = name

    positions = []
    for entity in included:
        if not _is_type(entity, "Position"):
            continue
        company = entity.get("companyName") or entity.get("company", {}).get("name")
        emp_urn = (
            entity.get("*employmentType")
            or entity.get("employmentTypeUrn")
            or entity.get("employmentType")
        )
        employment_type = None
        if isinstance(emp_urn, str):
            employment_type = employment_types.get(emp_urn)
        elif isinstance(emp_urn, dict):
            employment_type = emp_urn.get("name")

        positions.append(
            {
                "title": entity.get("title"),
                "company_name": company if isinstance(company, str) else None,
                "location": entity.get("locationName"),
                "description": entity.get("description"),
                "employment_type": employment_type,
                "date_range": _parse_date_range(
                    entity.get("dateRange") or entity.get("timePeriod")
                ),
            }
        )

    educations = []
    for entity in included:
        if not _is_type(entity, "Education"):
            continue
        school = entity.get("schoolName") or entity.get("school", {}).get("name")
        educations.append(
            {
                "school_name": school if isinstance(school, str) else None,
                "degree_name": entity.get("degreeName"),
                "field_of_study": entity.get("fieldOfStudy"),
                "grade": entity.get("grade"),
                "activities": entity.get("activities"),
                "description": entity.get("description"),
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
        certifications.append(
            {
                "name": entity.get("name"),
                "authority": entity.get("authority"),
                "url": entity.get("url"),
                "issue_date": _format_issue_date(entity),
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

    treasury_media = []
    for entity in included:
        if not _is_type(entity, "TreasuryMedia"):
            continue
        item = _parse_treasury_item(entity)
        if item:
            treasury_media.append(item)

    public_id = profile.get("publicIdentifier")
    skills_total, _, _ = skills_paging_info(raw)
    return {
        "first_name": profile.get("firstName"),
        "last_name": profile.get("lastName"),
        "headline": profile.get("headline"),
        "summary": profile.get("summary"),
        "public_identifier": public_id,
        "profile_url": f"https://www.linkedin.com/in/{public_id}/" if public_id else None,
        "urn": profile.get("entityUrn") or profile.get("objectUrn"),
        "location": _parse_location(profile, included),
        "profile_picture_url": profile_pic_url,
        "cover_picture_url": cover_pic_url,
        "positions": positions,
        "educations": educations,
        "skills": skills,
        "skills_total": skills_total if skills_total else len(skills),
        "certifications": certifications,
        "languages": languages,
        "treasury_media": treasury_media,
    }
