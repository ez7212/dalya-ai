"""
Property Finder / Bayut listing scraper.

Agents creating a finished-property listing paste a PF or Bayut URL. The
scraper extracts as much structured data as it can (project, community,
bedrooms, size, asking price, images, description) and returns a draft.
Anything that fails to parse is left as None — the route always returns a
partial draft so the agent's manual-entry form is prefilled with whatever
was retrieved. Failures must NEVER block the agent.

Implementation notes:
- Property Finder embeds full JSON-LD (`<script type="application/ld+json">`)
  on listing pages. We parse that first; fall back to meta-tag scraping.
- Bayut uses Next.js `__NEXT_DATA__` JSON blob. We parse that.
- All HTTP calls have short timeouts. Any exception → returns ScrapedListing
  with everything None.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)


_HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/17.0 Safari/605.1.15"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

_BAYUT_RAPIDAPI_HOST = "uae-real-estate-data-api-2.p.rapidapi.com"
_BAYUT_RAPIDAPI_URL = f"https://{_BAYUT_RAPIDAPI_HOST}/property-details"
_SQM_TO_SQFT = 10.76391041671


@dataclass
class ScrapedListing:
    source: str = ""
    source_url: str = ""
    property_type: str = "ready"          # PF/Bayut listings are typically ready stock
    listing_title: Optional[str] = None
    listing_reference: Optional[str] = None
    portal_listing_id: Optional[str] = None
    portal_reference: Optional[str] = None
    purpose: Optional[str] = None
    completion_status: Optional[str] = None
    furnishing: Optional[str] = None
    community: Optional[str] = None
    subcommunity: Optional[str] = None
    building_or_project: Optional[str] = None
    unit_number: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    size_sqft: Optional[float] = None
    plot_size_sqft: Optional[float] = None
    asking_price_aed: Optional[float] = None
    price_per_sqft_aed: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    developer: Optional[str] = None
    handover_date: Optional[str] = None
    permit_number: Optional[str] = None
    permit_validation_url: Optional[str] = None
    broker_name: Optional[str] = None
    broker_license: Optional[str] = None
    agent_name: Optional[str] = None
    agent_email: Optional[str] = None
    agent_phone: Optional[str] = None
    agent_license: Optional[str] = None
    amenities: list[str] = field(default_factory=list)
    image_urls: list[str] = field(default_factory=list)
    description: Optional[str] = None
    raw_extracts: dict = field(default_factory=dict)


def _detect_source(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if "propertyfinder" in host or "pf.com" in host:
        return "property_finder"
    if "bayut" in host:
        return "bayut"
    return "unknown"


def _safe_int(value) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _safe_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _sqm_to_sqft(value) -> Optional[float]:
    size_sqm = _safe_float(value)
    if size_sqm is None:
        return None
    return round(size_sqm * _SQM_TO_SQFT, 2)


def _fetch_html(url: str) -> Optional[str]:
    try:
        with httpx.Client(timeout=10, headers=_HTTP_HEADERS, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.text
    except Exception as exc:
        logger.warning("listing_scraper: failed to fetch %s: %s", url, exc)
        return None


def _parse_jsonld(html: str) -> list[dict]:
    blocks: list[dict] = []
    for match in re.finditer(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.IGNORECASE | re.DOTALL,
    ):
        try:
            payload = json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            blocks.append(payload)
        elif isinstance(payload, list):
            blocks.extend(p for p in payload if isinstance(p, dict))
    return blocks


def _parse_next_data(html: str) -> Optional[dict]:
    match = re.search(
        r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
        html,
        re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return None
    try:
        return json.loads(match.group(1).strip())
    except json.JSONDecodeError:
        return None


def _get_path(obj, *path):
    current = obj
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _append_unique(values: list[str], value: Optional[str]) -> None:
    if value and value not in values:
        values.append(value)


def _iso_date(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return value[:10]


def _walk_dicts(obj):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from _walk_dicts(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _walk_dicts(value)


def _first_dict_matching(obj, keys: set[str]) -> Optional[dict]:
    for candidate in _walk_dicts(obj):
        if keys.issubset(candidate.keys()):
            return candidate
    return None


def _first_value(obj, keys: tuple[str, ...]):
    if not isinstance(obj, dict):
        return None
    for key in keys:
        value = obj.get(key)
        if value not in (None, "", []):
            return value
    return None


def _stringify(value) -> Optional[str]:
    if value in (None, ""):
        return None
    return str(value)


def _money_value(value) -> Optional[float]:
    if isinstance(value, dict):
        value = _first_value(value, ("value", "amount", "price"))
    if isinstance(value, str):
        value = re.sub(r"[^\d.]", "", value)
    return _safe_float(value)


def _extract_location_names(value) -> list[str]:
    names: list[str] = []
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                name = item.get("name") or item.get("title")
                if name:
                    names.append(str(name))
            elif isinstance(item, str):
                names.append(item)
    elif isinstance(value, dict):
        for key in ("full_name", "fullName", "name", "title"):
            if value.get(key):
                names.append(str(value[key]))
        children = value.get("tree") or value.get("path") or value.get("locations")
        if isinstance(children, list):
            names.extend(_extract_location_names(children))
    elif isinstance(value, str):
        names.append(value)
    return [name for name in names if name]


def _extract_image_url(value) -> Optional[str]:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        direct_url = _first_value(value, ("url", "src", "full", "large", "medium", "main", "photo", "image", "original"))
        if direct_url:
            return direct_url
        image_id = _first_value(value, ("id", "externalID", "externalId", "photoID", "photoId"))
        if image_id:
            return f"https://images.bayut.com/thumbnails/{image_id}-800x600.webp"
    return None


def _extract_license_number(value) -> Optional[str]:
    if isinstance(value, dict):
        return _stringify(_first_value(value, ("licenseNumber", "license_number", "number", "rera", "orn")))
    if isinstance(value, list):
        for item in value:
            license_number = _extract_license_number(item)
            if license_number:
                return license_number
    return _stringify(value)


def _apply_bayut_location(out: ScrapedListing, value) -> None:
    location_names = _extract_location_names(value)
    if location_names:
        out.community = out.community or (location_names[-2] if len(location_names) > 1 else location_names[-1])
        out.subcommunity = out.subcommunity or location_names[-1]
    if not isinstance(value, dict):
        return
    community = value.get("community") if isinstance(value.get("community"), dict) else {}
    subcommunity = value.get("sub_community") or value.get("subCommunity")
    subcommunity = subcommunity if isinstance(subcommunity, dict) else {}
    cluster = value.get("cluster") if isinstance(value.get("cluster"), dict) else {}
    building = value.get("building") if isinstance(value.get("building"), dict) else {}
    out.community = out.community or _stringify(_first_value(community, ("name", "title")))
    out.subcommunity = out.subcommunity or _stringify(
        _first_value(subcommunity, ("name", "title")) or _first_value(cluster, ("name", "title"))
    )
    out.building_or_project = out.building_or_project or _stringify(_first_value(building, ("name", "title")))


def _append_bayut_amenities(out: ScrapedListing, value) -> None:
    if isinstance(value, list):
        for item in value:
            _append_bayut_amenities(out, item)
    elif isinstance(value, dict):
        _append_unique(out.amenities, _stringify(_first_value(value, ("text", "name", "title"))))
        nested = _first_value(value, ("items", "amenities", "features"))
        if nested is not None:
            _append_bayut_amenities(out, nested)
    else:
        _append_unique(out.amenities, _stringify(value))


def _append_bayut_images(out: ScrapedListing, value) -> None:
    if isinstance(value, list):
        for item in value:
            _append_bayut_images(out, item)
    elif isinstance(value, dict):
        _append_unique(out.image_urls, _extract_image_url(value))
        for key in ("cover_photo", "coverPhoto", "photos", "images", "items"):
            nested = value.get(key)
            if nested is not None:
                _append_bayut_images(out, nested)
    else:
        _append_unique(out.image_urls, _extract_image_url(value))


def _meta_content(html: str, prop: str) -> Optional[str]:
    pattern = re.compile(
        rf'<meta[^>]+(?:property|name)=["\']{re.escape(prop)}["\'][^>]+content=["\']([^"\']+)["\']',
        re.IGNORECASE,
    )
    match = pattern.search(html)
    return match.group(1) if match else None


def scrape_property_finder(url: str, html: Optional[str] = None) -> ScrapedListing:
    out = ScrapedListing(source="property_finder", source_url=url)
    html = html if html is not None else _fetch_html(url)
    if not html:
        return out

    next_data = _parse_next_data(html)
    property_result = _get_path(next_data or {}, "props", "pageProps", "propertyResult", "property")
    if isinstance(property_result, dict):
        out.raw_extracts["__NEXT_DATA__"] = True
        price = property_result.get("price") if isinstance(property_result.get("price"), dict) else {}
        location = property_result.get("location") if isinstance(property_result.get("location"), dict) else {}
        coordinates = location.get("coordinates") if isinstance(location.get("coordinates"), dict) else {}
        size = property_result.get("size") if isinstance(property_result.get("size"), dict) else {}
        project = property_result.get("project") if isinstance(property_result.get("project"), dict) else {}
        developer = project.get("developer") if isinstance(project.get("developer"), dict) else {}
        agent = property_result.get("agent") if isinstance(property_result.get("agent"), dict) else {}
        broker = property_result.get("broker") or property_result.get("client")
        broker = broker if isinstance(broker, dict) else {}
        rera = property_result.get("rera") if isinstance(property_result.get("rera"), dict) else {}
        price_per_area = property_result.get("price_per_area") if isinstance(property_result.get("price_per_area"), dict) else {}

        out.portal_listing_id = str(property_result.get("id") or "") or None
        out.portal_reference = property_result.get("listing_id")
        out.listing_reference = property_result.get("reference")
        out.listing_title = property_result.get("title")
        out.purpose = "sale" if price.get("period") == "sell" else price.get("period")
        out.property_type = property_result.get("property_type") or out.property_type
        out.completion_status = property_result.get("completion_status")
        out.furnishing = property_result.get("furnished")
        out.community = location.get("path_name", "").split(", ")[-1] if location.get("path_name") else out.community
        out.subcommunity = location.get("name")
        out.building_or_project = project.get("title") or location.get("name") or out.building_or_project
        out.bedrooms = _safe_int(property_result.get("bedrooms_value") or property_result.get("bedrooms"))
        out.bathrooms = _safe_int(property_result.get("bathrooms_value") or property_result.get("bathrooms"))
        out.size_sqft = _safe_float(size.get("value") or property_result.get("plot_size"))
        out.plot_size_sqft = _safe_float(property_result.get("plot_size"))
        out.asking_price_aed = _safe_float(price.get("value"))
        out.price_per_sqft_aed = _safe_float(price_per_area.get("price"))
        out.latitude = _safe_float(coordinates.get("lat"))
        out.longitude = _safe_float(coordinates.get("lon"))
        out.developer = developer.get("name")
        out.handover_date = _iso_date(project.get("delivery_date"))
        out.permit_number = rera.get("number")
        out.permit_validation_url = rera.get("permit_validation_url")
        out.broker_name = broker.get("name")
        out.broker_license = broker.get("license_number")
        out.agent_name = agent.get("name")
        out.agent_email = agent.get("email")
        out.agent_license = property_result.get("agent_license_no") or None
        for license_item in property_result.get("licenses") or []:
            if isinstance(license_item, dict) and license_item.get("license_type") == "brn":
                out.agent_license = out.agent_license or license_item.get("license_number")
        for contact in property_result.get("contact_options") or []:
            if isinstance(contact, dict) and contact.get("type") == "phone":
                out.agent_phone = out.agent_phone or contact.get("value")
        out.description = property_result.get("description")
        for amenity in property_result.get("amenities") or []:
            if isinstance(amenity, dict):
                _append_unique(out.amenities, amenity.get("name"))
        images = property_result.get("images") if isinstance(property_result.get("images"), dict) else {}
        for image in images.get("property") or []:
            if isinstance(image, dict):
                _append_unique(out.image_urls, image.get("full") or image.get("medium") or image.get("small"))

    # JSON-LD: PF listing pages typically include a Product / Residence object
    for block in _parse_jsonld(html):
        t = block.get("@type")
        if isinstance(t, list):
            t = t[0] if t else None
        if t in ("Product", "Residence", "Place", "RealEstateListing", "Offer"):
            out.raw_extracts.setdefault("jsonld", []).append(block)
            out.description = out.description or block.get("description")
            out.listing_title = out.listing_title or block.get("name")
            offers = block.get("offers") or {}
            if isinstance(offers, list):
                offers = offers[0] if offers and isinstance(offers[0], dict) else {}
            if isinstance(offers, dict):
                out.asking_price_aed = out.asking_price_aed or _safe_float(offers.get("price"))
                price_spec = offers.get("priceSpecification")
                if isinstance(price_spec, dict):
                    out.asking_price_aed = out.asking_price_aed or _safe_float(price_spec.get("price"))
                offered_by = offers.get("offeredBy")
                if isinstance(offered_by, dict):
                    out.agent_name = out.agent_name or offered_by.get("name")
                    out.agent_phone = out.agent_phone or offered_by.get("telephone")
                    org = offered_by.get("parentOrganization")
                    if isinstance(org, dict):
                        out.broker_name = out.broker_name or org.get("name")
            address = block.get("address") or {}
            if isinstance(address, dict):
                out.community = out.community or address.get("addressLocality") or address.get("addressRegion")
                out.subcommunity = out.subcommunity or address.get("name")
            geo = block.get("geo") or {}
            if isinstance(geo, dict):
                out.latitude = out.latitude or _safe_float(geo.get("latitude"))
                out.longitude = out.longitude or _safe_float(geo.get("longitude"))
            floor_size = block.get("floorSize") or {}
            if isinstance(floor_size, dict):
                out.size_sqft = out.size_sqft or _safe_float(floor_size.get("value"))
            image = block.get("image")
            if isinstance(image, list):
                for x in image:
                    _append_unique(out.image_urls, str(x))
            elif isinstance(image, str):
                _append_unique(out.image_urls, image)
            for amenity in block.get("amenityFeature") or []:
                if isinstance(amenity, dict):
                    _append_unique(out.amenities, amenity.get("name"))

    # Meta tags
    out.description = out.description or _meta_content(html, "og:description") or _meta_content(html, "description")
    out.listing_title = out.listing_title or _meta_content(html, "og:title")
    image = _meta_content(html, "og:image")
    _append_unique(out.image_urls, image)

    # Best-effort regex for bedrooms / size in description
    if out.description:
        bed_match = re.search(r"(\d+)\s*(?:bed|bedroom)", out.description, re.IGNORECASE)
        if bed_match:
            out.bedrooms = out.bedrooms or _safe_int(bed_match.group(1))
        size_match = re.search(r"([\d,]+)\s*(?:sq\.?\s*ft|sqft|square\s*feet)", out.description, re.IGNORECASE)
        if size_match:
            out.size_sqft = out.size_sqft or _safe_float(size_match.group(1).replace(",", ""))

    return out


def scrape_bayut(url: str, html: Optional[str] = None) -> ScrapedListing:
    out = ScrapedListing(source="bayut", source_url=url)
    id_match = re.search(r"(?:details-|property/details-)(\d+)", url)
    if id_match:
        out.portal_listing_id = id_match.group(1)
    if out.portal_listing_id and html is None:
        api_payload = _fetch_bayut_rapidapi(out.portal_listing_id)
        if api_payload:
            out.raw_extracts["rapidapi"] = True
            _apply_bayut_api_payload(out, api_payload)
            if out.asking_price_aed or out.listing_title or out.size_sqft:
                return out
    html = html if html is not None else _fetch_html(url)
    if not html:
        return out

    if "<title>Captcha | Bayut</title>" in html:
        out.raw_extracts["captcha"] = True
        return out

    for block in _parse_jsonld(html):
        out.raw_extracts.setdefault("jsonld", []).append(block)
        out.listing_title = out.listing_title or block.get("name")
        out.description = out.description or block.get("description")
        offers = block.get("offers")
        if isinstance(offers, list):
            offers = offers[0] if offers and isinstance(offers[0], dict) else {}
        if isinstance(offers, dict):
            out.asking_price_aed = out.asking_price_aed or _safe_float(offers.get("price"))
            out.purpose = out.purpose or "sale"
        address = block.get("address")
        if isinstance(address, dict):
            out.community = out.community or address.get("addressRegion") or address.get("addressLocality")
            out.subcommunity = out.subcommunity or address.get("streetAddress")
        image = block.get("image")
        if isinstance(image, list):
            for img in image:
                _append_unique(out.image_urls, str(img))
        elif isinstance(image, str):
            _append_unique(out.image_urls, image)

    next_data = _parse_next_data(html)
    if next_data:
        # Bayut nests the property under props.pageProps.propertyDetails or similar
        out.raw_extracts["__NEXT_DATA__"] = True
        try:
            props = next_data.get("props", {}).get("pageProps", {}) if isinstance(next_data.get("props"), dict) else {}
            # Common shapes — try a few keys
            candidates = []
            for key in ("propertyDetails", "property", "data"):
                v = props.get(key)
                if isinstance(v, dict):
                    candidates.append(v)
            if not candidates and isinstance(props, dict):
                candidates.append(props)

            for c in candidates:
                out.asking_price_aed = out.asking_price_aed or _safe_float(
                    c.get("price") or c.get("priceValue") or (c.get("price_value") if isinstance(c, dict) else None)
                )
                out.bedrooms = out.bedrooms or _safe_int(c.get("rooms") or c.get("bedrooms"))
                out.size_sqft = out.size_sqft or _safe_float(
                    c.get("area") or c.get("size") or c.get("area_value")
                )
                out.description = out.description or c.get("description") or c.get("title")
                out.building_or_project = out.building_or_project or c.get("buildingName") or c.get("project")
                loc = c.get("location") or {}
                if isinstance(loc, list) and loc:
                    out.community = out.community or (loc[-1].get("name") if isinstance(loc[-1], dict) else None)
                elif isinstance(loc, dict):
                    out.community = out.community or loc.get("name")
                imgs = c.get("photos") or c.get("images") or []
                if isinstance(imgs, list):
                    for img in imgs:
                        if isinstance(img, str):
                            _append_unique(out.image_urls, img)
                        elif isinstance(img, dict):
                            url_img = img.get("url") or img.get("src")
                            if url_img:
                                _append_unique(out.image_urls, url_img)
        except Exception as exc:
            logger.warning("bayut __NEXT_DATA__ parse failure: %s", exc)

    state_match = re.search(
        r'<script[^>]+id=["\'](?:__PRELOADED_STATE__|__INITIAL_STATE__)["\'][^>]*>(.*?)</script>',
        html,
        re.IGNORECASE | re.DOTALL,
    )
    if state_match:
        try:
            state = json.loads(state_match.group(1).strip())
            out.raw_extracts["state_json"] = True
            ad = _first_dict_matching(state, {"price", "title", "location"})
            if ad:
                out.portal_listing_id = out.portal_listing_id or str(ad.get("externalID") or ad.get("id") or "") or None
                out.listing_reference = out.listing_reference or ad.get("referenceNumber") or ad.get("reference")
                out.listing_title = out.listing_title or ad.get("title")
                out.property_type = ad.get("category", [{}])[-1].get("name") if isinstance(ad.get("category"), list) and ad.get("category") else out.property_type
                out.asking_price_aed = out.asking_price_aed or _safe_float(ad.get("price"))
                out.bedrooms = out.bedrooms or _safe_int(ad.get("rooms") or ad.get("bedrooms"))
                out.bathrooms = out.bathrooms or _safe_int(ad.get("baths") or ad.get("bathrooms"))
                out.size_sqft = out.size_sqft or _safe_float(ad.get("area") or ad.get("size"))
                out.description = out.description or ad.get("description")
                loc = ad.get("location")
                if isinstance(loc, list) and loc:
                    names = [item.get("name") for item in loc if isinstance(item, dict) and item.get("name")]
                    if names:
                        out.community = out.community or (names[-2] if len(names) > 1 else names[-1])
                        out.subcommunity = out.subcommunity or names[-1]
                elif isinstance(loc, dict):
                    out.community = out.community or loc.get("name")
                for amenity in ad.get("amenities") or []:
                    if isinstance(amenity, dict):
                        _append_unique(out.amenities, amenity.get("text") or amenity.get("name"))
                    elif isinstance(amenity, str):
                        _append_unique(out.amenities, amenity)
                for photo in ad.get("photos") or ad.get("images") or []:
                    if isinstance(photo, dict):
                        _append_unique(out.image_urls, photo.get("url") or photo.get("main") or photo.get("large"))
                    elif isinstance(photo, str):
                        _append_unique(out.image_urls, photo)
        except Exception as exc:
            logger.warning("bayut embedded state parse failure: %s", exc)

    # Fallback meta tags
    out.description = out.description or _meta_content(html, "og:description")
    out.listing_title = out.listing_title or _meta_content(html, "og:title")
    image = _meta_content(html, "og:image")
    _append_unique(out.image_urls, image)

    title_blob = " ".join(
        value
        for value in [out.listing_title, out.description]
        if value
    )
    if title_blob and not out.bedrooms:
        bed_match = re.search(r"(\d+)\s*(?:bed|bedroom|br)\b", title_blob, re.IGNORECASE)
        if bed_match:
            out.bedrooms = _safe_int(bed_match.group(1))
    if title_blob and not out.size_sqft:
        size_match = re.search(r"([\d,]+)\s*(?:sq\.?\s*ft|sqft)", title_blob, re.IGNORECASE)
        if size_match:
            out.size_sqft = _safe_float(size_match.group(1).replace(",", ""))

    return out


def _payload_has_provider_error(payload: dict) -> bool:
    status_code = _safe_int(payload.get("status_code") or payload.get("statusCode") or payload.get("code"))
    data = payload.get("data")
    message = _stringify(payload.get("message"))
    success = payload.get("success")
    if success is False:
        return True
    if status_code and status_code >= 400:
        return True
    return message == "Error" and data in (None, "", [], {})


def _fetch_rapidapi_json(url: str, host: str, api_key: str, params: dict) -> Optional[dict]:
    try:
        with httpx.Client(timeout=15) as client:
            response = client.get(
                url,
                params=params,
                headers={
                    "Content-Type": "application/json",
                    "x-rapidapi-host": host,
                    "x-rapidapi-key": api_key,
                },
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or _payload_has_provider_error(payload):
                return None
            return payload
    except (httpx.HTTPError, json.JSONDecodeError) as exc:
        logger.warning("bayut rapidapi fetch failed for host %s: %s", host, exc)
        return None


def _fetch_bayut_rapidapi(property_external_id: str) -> Optional[dict]:
    api_key = os.getenv("BAYUT_RAPIDAPI_KEY") or os.getenv("RAPIDAPI_KEY")
    if not api_key:
        return None
    return _fetch_rapidapi_json(
        _BAYUT_RAPIDAPI_URL,
        _BAYUT_RAPIDAPI_HOST,
        api_key,
        {"langs": "en", "external_id": property_external_id},
    )


def _apply_bayut_api_payload(out: ScrapedListing, payload: dict) -> None:
    candidates = [
        payload,
        payload.get("data") if isinstance(payload.get("data"), dict) else None,
        payload.get("property") if isinstance(payload.get("property"), dict) else None,
        payload.get("result") if isinstance(payload.get("result"), dict) else None,
        payload.get("ad") if isinstance(payload.get("ad"), dict) else None,
        payload.get("listing") if isinstance(payload.get("listing"), dict) else None,
    ]
    candidate = next((item for item in candidates if isinstance(item, dict) and len(item) > 3), payload)
    ad = _first_dict_matching(candidate, {"price", "title"}) or _first_dict_matching(candidate, {"externalID"}) or candidate

    out.portal_listing_id = out.portal_listing_id or _stringify(
        _first_value(ad, ("externalID", "externalId", "property_external_id", "id", "objectID"))
    )
    out.portal_reference = out.portal_reference or _stringify(_first_value(ad, ("objectID", "sourceID", "id")))
    out.listing_reference = out.listing_reference or _stringify(
        _first_value(ad, ("referenceNumber", "reference", "reference_number", "referenceNo"))
    )
    out.listing_title = out.listing_title or _stringify(_first_value(ad, ("title", "name")))
    out.description = out.description or _stringify(_first_value(ad, ("description", "descriptionTranslated")))

    purpose = _stringify(_first_value(ad, ("purpose", "offering_type", "offeringType")))
    if purpose:
        out.purpose = "sale" if "sale" in purpose.lower() else "rent" if "rent" in purpose.lower() else purpose

    category = _first_value(ad, ("category", "propertyType", "property_type", "type"))
    if isinstance(category, list) and category:
        last = category[-1]
        out.property_type = _stringify(last.get("name") if isinstance(last, dict) else last) or out.property_type
    elif isinstance(category, dict):
        out.property_type = _stringify(_first_value(category, ("name", "title", "slug"))) or out.property_type
    else:
        out.property_type = _stringify(category) or out.property_type

    out.asking_price_aed = out.asking_price_aed or _money_value(_first_value(ad, ("price", "priceValue", "price_value")))
    out.bedrooms = out.bedrooms or _safe_int(_first_value(ad, ("rooms", "bedrooms", "beds")))
    out.bathrooms = out.bathrooms or _safe_int(_first_value(ad, ("baths", "bathrooms")))
    out.size_sqft = out.size_sqft or (
        _safe_float(_first_value(ad, ("bua_sqft", "size_sqft")))
        or _sqm_to_sqft(_first_value(ad, ("area", "size", "builtUpArea", "bua")))
    )
    out.plot_size_sqft = out.plot_size_sqft or (
        _safe_float(_first_value(ad, ("plot_size_sqft",)))
        or _sqm_to_sqft(_first_value(ad, ("plotArea", "plot_area", "plotSize", "plotSizeSqm")))
    )
    if out.asking_price_aed and out.size_sqft and not out.price_per_sqft_aed:
        out.price_per_sqft_aed = round(out.asking_price_aed / out.size_sqft, 2)

    details = ad.get("details") if isinstance(ad.get("details"), dict) else {}
    out.completion_status = out.completion_status or _stringify(
        _first_value(ad, ("completionStatus", "completion_status"))
        or _first_value(details, ("completionStatus", "completion_status"))
    )
    out.furnishing = out.furnishing or _stringify(
        _first_value(ad, ("furnishingStatus", "furnished", "furnishing", "furnishing_status"))
        or _first_value(details, ("furnishingStatus", "furnishing_status", "furnished", "furnishing"))
    )

    _apply_bayut_location(out, _first_value(ad, ("location", "geography", "locations")))
    out.building_or_project = out.building_or_project or _stringify(
        _first_value(ad, ("project", "projectName", "project_name", "buildingName", "building"))
    )
    if isinstance(ad.get("project"), dict):
        project = ad["project"]
        out.building_or_project = out.building_or_project or _stringify(_first_value(project, ("name", "title")))
        developer = project.get("developer")
        if isinstance(developer, dict):
            out.developer = out.developer or _stringify(_first_value(developer, ("name", "title")))
        else:
            out.developer = out.developer or _stringify(developer)
    offplan = _first_value(ad, ("offplanDetails", "offplan_details"))
    if isinstance(offplan, dict):
        out.handover_date = out.handover_date or _iso_date(
            _stringify(_first_value(offplan, ("handoverDate", "handover_date", "deliveryDate", "completionDate")))
        )
        out.developer = out.developer or _stringify(_first_value(offplan, ("developer", "developerName")))

    coordinates = _first_value(ad, ("coordinates", "geo", "geography"))
    if isinstance(coordinates, dict):
        out.latitude = out.latitude or _safe_float(_first_value(coordinates, ("lat", "latitude")))
        out.longitude = out.longitude or _safe_float(_first_value(coordinates, ("lon", "lng", "longitude")))

    agency = ad.get("agency") if isinstance(ad.get("agency"), dict) else {}
    out.broker_name = out.broker_name or _stringify(_first_value(agency, ("name", "title")))
    out.broker_license = out.broker_license or (
        _stringify(_first_value(agency, ("licenseNumber", "license_number", "rera", "orn")))
        or _extract_license_number(agency.get("licenses"))
    )
    agent = ad.get("agent") if isinstance(ad.get("agent"), dict) else {}
    out.agent_name = out.agent_name or _stringify(_first_value(ad, ("contactName", "agentName", "agent_name")) or _first_value(agent, ("name", "title")))
    out.agent_email = out.agent_email or _stringify(_first_value(agent, ("email", "emailAddress")))
    out.agent_phone = out.agent_phone or _stringify(_first_value(ad, ("phoneNumber", "phone", "mobile")) or _first_value(agent, ("phone", "phoneNumber", "mobile")))
    out.agent_license = out.agent_license or _extract_license_number(agent.get("licenses"))

    verification = ad.get("verification") if isinstance(ad.get("verification"), dict) else {}
    legal = ad.get("legal") if isinstance(ad.get("legal"), dict) else {}
    out.permit_number = out.permit_number or _stringify(
        _first_value(ad, ("permitNumber", "permit_number", "dldPermitNumber"))
        or _first_value(verification, ("permitNumber", "permit_number", "truCheckPermitNumber"))
        or _first_value(legal, ("permitNumber", "permit_number", "dldPermitNumber"))
    )

    _append_bayut_amenities(out, _first_value(ad, ("amenities", "features")))

    for image_group_key in ("photos", "images", "photoIDs", "coverPhoto", "imageUrls"):
        images = ad.get(image_group_key)
        _append_bayut_images(out, images)
    _append_bayut_images(out, ad.get("media"))


def scrape_any(url: str, html: Optional[str] = None) -> ScrapedListing:
    """
    Detect the platform from the URL and dispatch. Failures fall through to a
    partial draft — never raise.
    """
    if not url:
        return ScrapedListing(source="unknown", source_url=url or "")
    source = _detect_source(url)
    try:
        if source == "property_finder":
            return scrape_property_finder(url, html=html)
        if source == "bayut":
            return scrape_bayut(url, html=html)
        return ScrapedListing(source="unknown", source_url=url)
    except Exception as exc:
        logger.warning("listing_scraper: unexpected failure scraping %s: %s", url, exc)
        return ScrapedListing(source=source, source_url=url)
