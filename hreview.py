import re
from typing import Dict, Tuple

import mf2py
import requests
from bs4 import BeautifulSoup

from config import API_URL

addyourself = "{{" + "addyourself" + "}}"


def create_infobox(latitude: int, longitude: int, page_text: str) -> Tuple[str, str]:
    """
    Creates an infobox with location information about a place.

    :param latitude: Latitude of the place
    :type latitude: float
    :param longitude: Longitude of the place
    :type longitude: float
    :param page_text: The text of the wiki page to create
    :return: A tuple with the text of the page with the infobox added and the address of the place
    :rtype: Tuple[str, str]
    """
    # if section does not exist, create it
    try:
        nominatim_information = requests.get(
            f"https://nominatim.openstreetmap.org/reverse?lat={latitude}&lon={longitude}&format=json"
        )
    except requests.exceptions.RequestException:
        pass

    address = nominatim_information.json()["address"]

    address_string = f"{address['road']}, {address['postcode']} {address['city']}, {address['country']}"

    infobox = f"""
    Infobox
    |location={address['city']}, {address['country']}
    |lat={latitude}
    |long={longitude}
    |address={address_string}
    """

    page_text += "{{" + infobox + "}}"

    return page_text, address


def update_existing_review_section(
    review_section_start: int,
    content_url: str,
    h_review: str,
    domain: str,
    page_text: str,
) -> str:
    """
    Adds a new review to an existing review section.

    :param review_section_start: The index of the start of the review section
    :type review_section_start: int
    :param content_url: The URL of the new review
    :type content_url: str
    :param h_review: The h-review object that contains the new review
    :type h_review: str
    :param domain: The domain of the person who wrote the review
    :type domain: str
    :param page_text: The text of the wiki page to create
    :type page_text: str
    :return: The text of the page with the new review added and an updateed aggregate review
    :rtype: str
    """
    page_text_after_reviews = page_text[review_section_start:]

    page_text += f"""
        <div class='h-review'>
            \n=== <a href='{content_url}' class='p-name'>{h_review['name'][0]}</a>
            by {domain} -
             <data value='{h_review['rating'][0]}' class='p-rating'>{h_review['rating'][0]} stars</data>
            ===\n
        <blockquote>{h_review['content'][0]['html']}</blockquote></div>"""

    page_text = page_text[:review_section_start] + page_text_after_reviews

    aggregate_ratings = mf2py.parse(doc=page_text)

    ratings = [
        int(r["properties"]["rating"][0])
        for r in aggregate_ratings["items"][0]["children"]
        if r["type"][0] == "h-review"
    ]

    stars = str(round(sum(ratings) / len(ratings), 1))

    # get h-review-aggregate
    page_text_aggregate = re.search(
        r"<div class='h-review-aggregate'>.*?</div>", page_text, re.DOTALL
    )
    page_text_aggregate = page_text_aggregate.group(0)

    star_no_decimal_places = round(stars)

    star_emojis = "⭐" * star_no_decimal_places

    # replace h-review-aggregate
    page_text = page_text.replace(
        page_text_aggregate,
        f"""\n\n<div class='h-review-aggregate'>
            <span class='p-item'>{h_review['name'][0]}</span>
            aggregate review: {star_emojis} -
            <data value='{stars}' class='p-average'>{stars}</data>
            /<data value='5' class='p-best'>5</data>
             (<data value='{len(ratings)}' class='p-votes'>{len(ratings)}</data>
            ratings)</div>\n\n{addyourself}\n""",
    )

    return page_text


def create_new_review_section(
    address: dict, content_url: str, h_review: dict, domain: str, page_text: str
) -> str:
    """
    Creates a new "Reviews" section at the bottom of a wiki page.

    :param address: The address of the topic of the page
    :type address: dict
    :param content_url: The URL of the new review
    :type content_url: str
    :param h_review: The h-review object that contains the new review
    :type h_review: dict
    :param domain: The domain of the person who wrote the review
    :type domain: str
    :param page_text: The text of the wiki page to create
    :type page_text: str
    :return: The text of the page with a new reviews section and categories set
        for the city and country of the place being reviewed
    """
    star_no_decimal_places = round(h_review["rating"][0])

    star_emojis = "⭐" * star_no_decimal_places

    page_text += "\n\n<div class='h-feed'>\n== Reviews ==\n\n"

    page_text += f"""<div class='h-review'>\n===
        <a href='{content_url}' class='p-name'>{h_review['name'][0]}</a>
        by {domain} -
         <data value='{h_review['rating'][0]}' class='p-rating'>{h_review['rating'][0]} stars</data> ===\n
        <blockquote>{h_review['content'][0]['html']}</blockquote></div>"""

    page_text += f"""\n
        <div class='h-review-aggregate'>
            <span class='p-item'>{h_review['name'][0]}</span> aggregate review: {star_emojis}
            - <data value='{h_review['rating'][0]}' class='p-average'>{h_review['rating'][0]}</data>
            /<data value='5' class='p-best'>5</data>
            (<data value='1' class='p-votes'>1</data> rating)\n
            {addyourself}
        </div>"""

    page_text += f"[[Category:{address['city']}]]"
    page_text += f"[[Category:{address['country']}]]"

    return page_text


def parse_h_review(
    h_review: dict, content_parsed: dict, content_url: str, domain: str
) -> Dict[str, str]:
    """
    Parses a h-review object and returns the contents for the new or revised wiki page.

    :param h_review: The h-review object to parse
    :type h_review: dict
    :param content_parsed: The parsed microformats of the page, used to look for a h-geo object
    :type content_parsed: dict
    :param content_url: The URL of the page that contains the review
    :type content_url: str
    :param domain: The domain of the person who wrote the review
    :type domain: str
    :return: The information needed to create the new wiki page.
    :rtype: Dict[str, str]
    """
    page_content = {
        "action": "query",
        "prop": "revisions",
        "titles": h_review["name"][0].replace(" - ", " ").replace(" ", "_"),
        "rvslots": "*",
        "rvprop": "content",
        "formatversion": "2",
        "format": "json",
    }

    try:
        page_content_request = requests.post(API_URL, params=page_content)

        page_text = page_content_request.json()["query"]["pages"][0]["revisions"][0][
            "slots"
        ]["main"]["content"]
    except Exception:
        page_text = ""

    # get == Reviews == section
    review_section_start = page_text.find("== Reviews ==")
    h_review["content"][0]["html"] = (
        BeautifulSoup(h_review["content"][0]["html"], "html.parser")
        .get_text()
        .replace("\n", " ")
    )

    h_geo = [
        e for e in content_parsed["items"][0]["children"] if e["type"][0] == "h-geo"
    ]

    if h_geo:
        latitude = h_geo[0]["properties"]["latitude"][0]
        longitude = h_geo[0]["properties"]["longitude"][0]
    else:
        latitude = None
        longitude = None

    if review_section_start == -1:
        page_text, address = create_infobox(latitude, longitude, page_text)

        page_text = create_new_review_section(
            address, content_url, h_review, domain, page_text
        )
    else:
        page_text = update_existing_review_section(
            review_section_start, content_url, h_review, domain, page_text
        )

    content_details = {
        "name": h_review["name"][0],
        "content": {"html": page_text},
        "url": content_url,
    }

    return content_details
