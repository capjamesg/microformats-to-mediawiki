from typing import Dict, Tuple
from urllib.parse import urlparse as urlparse_func

import mf2py
import requests

from config import LGNAME, LGPASSWORD, SYNDICATION_LINK
from hreview import parse_h_review


class SyndicationLinkNotPresent(Exception):
    pass


class UserNotAuthorized(Exception):
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


def get_list_of_authorized_users(url: str, session: requests.Session) -> Dict[str, str]:
    get_list_of_authorized_users_params = {
        "action": "query",
        "list": "allusers",
        "format": "json",
    }

    try:
        list_of_authorized_users_request = session.get(
            url, params=get_list_of_authorized_users_params
        )
    except requests.exceptions.RequestException:
        raise Exception

    authorized_users = list_of_authorized_users_request.json()["query"]["allusers"]

    dictionary_of_authorized_users = {k["name"].lower(): "" for k in authorized_users}

    return dictionary_of_authorized_users


def verify_user_is_authorized(
    url: str, user_domain: str, session: requests.Session
) -> None:
    authorized_users = get_list_of_authorized_users(url, session)

    if not authorized_users.get(user_domain.lower()):
        raise UserNotAuthorized


def parse_url(
    content_url: str, csrf_token_request: requests.Response
) -> Tuple[Dict[str, str], str]:
    content_parsed = mf2py.parse(url=content_url)

    h_review = [e for e in content_parsed["items"] if e["type"][0] == "h-review"][0][
        "properties"
    ]

    domain = urlparse_func(content_url).netloc

    csrf_token = csrf_token_request.json()["query"]["tokens"]["csrftoken"]

    if h_review:
        content_details = parse_h_review(h_review, content_parsed, content_url, domain)

        return content_details, csrf_token

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

    content_details["content"]["html"] = (
        content_details["content"]["html"]
        + f"\nThis page was originally created on {content_details['url']}."
    )

    # add p-category properties to main article content
    content_details["content"]["html"] = content_details["content"]["html"] + "\n".join(
        categories
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
        "summary": f"New page created by coffeebot from {content_details['url']}",
        "token": csrf_token,
        "bot": False,
    }

    try:
        session.post(api_url, data=edit_page_params)
    except requests.exceptions.RequestException:
        raise Exception
