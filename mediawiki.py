from typing import Dict, Tuple

import mf2py
import requests

from config import LGNAME, LGPASSWORD, SYNDICATION_LINK

class SyndicationLinkNotPresent(Exception):
    pass


def get_login_token_state(url: str) -> Tuple[requests.Session, requests.Response]:
    session = requests.Session()

    # get token
    params = {"action": "query", "meta": "tokens", "format": "json", "type": "login"}

    try:
        token_request = session.get(url, params=params)
    except requests.exceptions.RequestException:
        raise Exception

    return token_request, session


def log_in(
    url: str, token_request: str, session: requests.Session
) -> requests.Response:
    login_token = token_request.json()["query"]["tokens"]["logintoken"]

    request_to_log_in_params = {
        "action": "login",
        "lgname": LGNAME,
        "lgpassword": LGPASSWORD,
        "lgtoken": login_token,
        "format": "json",
    }

    try:
        session.post(url, data=request_to_log_in_params)
    except requests.exceptions.RequestException:
        raise Exception


def get_csrf_token(url: str, session: requests.Session) -> requests.Response:
    get_csrf_token_params = {"action": "query", "meta": "tokens", "format": "json"}

    try:
        csrf_token_request = session.get(url, params=get_csrf_token_params)
    except requests.exceptions.RequestException:
        raise Exception

    return csrf_token_request


def parse_url(
    content_url: str, csrf_token_request: requests.Response
) -> Tuple[Dict[str, str], str]:
    content_parsed = mf2py.parse(url=content_url)

    h_entry = [e for e in content_parsed["items"] if e["type"][0] == "h-entry"][0][
        "properties"
    ]

    categories = [f"[[Category:{c}]]" for c in h_entry["category"]]

    # check for syndication link
    if not h_entry.get("syndication"):
        raise SyndicationLinkNotPresent
        
    if not SYNDICATION_LINK in h_entry.get("syndication"):
        raise SyndicationLinkNotPresent


    content_details = {
        "name": h_entry["name"][0],
        "content": h_entry["content"][0],
        "url": h_entry["url"][0],
    }

    csrf_token = csrf_token_request.json()["query"]["tokens"]["csrftoken"]

    content_details["content"]["html"] = (
        content_details["content"]["html"]
        + f"\nThis page was originally created on {content_details['url']}."
    )

    # add p-category properties to main article content
    content_details["content"]["html"] = (
        content_details["content"]["html"]
        + "\n".join(categories)
    )

    return content_details, csrf_token


def submit_edit_request(
    content_details: Dict[str, str],
    session: requests.Session,
    api_url: str,
    csrf_token: str,
) -> None:
    # edit a page
    edit_page_params = {
        "action": "edit",
        "title": content_details["name"],
        "text": content_details["content"]["html"],
        "format": "json",
        "summary": "New page created by coffeebot",
        "token": csrf_token,
        "bot": False,
    }

    try:
        session.post(api_url, data=edit_page_params)
    except requests.exceptions.RequestException:
        raise Exception
    