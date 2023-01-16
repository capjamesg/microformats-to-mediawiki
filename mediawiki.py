from typing import Any, Dict, Tuple
from urllib.parse import urlparse as urlparse_func

import mf2py
import requests

from config import API_URL, LGNAME, LGPASSWORD, SYNDICATION_LINK
from hreview import parse_h_review, get_all_h_geos


class SyndicationLinkNotPresent(Exception):
    """
    A u-syndication link is not present on a page.

    See more about this link on the IndieWeb wiki:

    https://indieweb.org/u-syndication
    """

    pass


class UserNotAuthorized(Exception):
    """
    A user is not authorised to edit the MediaWiki page.
    """

    pass

def update_map_on_category_page(category):
    # get h-geos on all https://breakfastand.coffee/api.php?format=json&action=query&generator=categorymembers&gcmtype=page&gcmlimit=max&gcmtitle=Category:Leeds pages
    url = "https://breakfastand.coffee/api.php?format=json&action=query&generator=categorymembers&gcmtype=page&gcmlimit=max&gcmtitle=Category:" + category

    r = requests.get(url)

    if r.status_code != 200:
        raise Exception

    data = r.json()

    pages = data["query"]["pages"]

    h_geos = []

    for p in pages:
        h_geos.extend(get_all_h_geos(["https://breakfastand.coffee/" + pages[p]["title"]]))

    url = "map?coordinates=" + "".join([str(h_geo["properties"]["latitude"][0]) + "," + str(h_geo["properties"]["longitude"][0]) + "|" for h_geo in h_geos]).rstrip("|")

    content_details = {
        "name": "Category:" + category,
        "content": {"html": "<iframe path=\"" + url + "\" width=\"100%\" height=\"600px\" key=\"cbc\" />"},
        "url": "https://breakfastand.coffee/" + category,
    }

    session = requests.Session()

    token_request, session = get_login_token_state(API_URL)

    log_in(API_URL, token_request, session)

    csrf_token_request = get_csrf_token(API_URL, session)

    submit_edit_request(
        content_details,
        session,
        API_URL,
        csrf_token_request,
    )


def get_login_token_state(url: str) -> Tuple[requests.Response, requests.Session]:
    """
    Gets a login token from the MediaWiki API.

    :param url: The URL of the MediaWiki API.
    :type url: str
    :return: A tuple containing the session and the login token request.
    :rtype: Tuple[requests.Session, requests.Response]

    :raises requests.exceptions.RequestException: If the request to get the login token fails.
    """
    session = requests.Session()

    # get token
    params = {"action": "query", "meta": "tokens", "format": "json", "type": "login"}

    try:
        token_request = session.get(url, params=params)
    except requests.exceptions.RequestException as exception:
        raise exception

    return token_request, session


def log_in(url: str, token_request: requests.Response, session: requests.Session):
    """
    Log in to the MediaWiki API.

    :param url: The URL of the MediaWiki API.
    :type url: str
    :param token_request: A login token response retrieved from the MediaWiki API.
    :type token_request: requests.Response
    :param session: A session object used to make requests to the API.
    :type session: requests.Session
    """
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


def get_csrf_token(url: str, session: requests.Session) -> str:
    """
    Gets a CSRF token from the MediaWiki API.

    :param url: The URL of the MediaWiki API.
    :type url: str
    :param session: A session object used to make requests to the API.
    :type session: requests.Session

    :return: A CSRF token response from the MediaWiki API.
    :rtype: requests.Response
    """
    get_csrf_token_params = {"action": "query", "meta": "tokens", "format": "json"}

    try:
        csrf_token_request = session.get(url, params=get_csrf_token_params)
    except requests.exceptions.RequestException:
        raise Exception

    csrf_token = csrf_token_request.json()["query"]["tokens"]["csrftoken"]

    return csrf_token


def get_list_of_authorized_users(url: str, session: requests.Session) -> Dict[str, str]:
    """
    Gets a list of all users on a MediaWiki.

    :param url: The URL of the MediaWiki API.
    :type url: str
    :param session: A session object used to make requests to the API.
    :type session: requests.Session
    :return: A dictionary of all users on the MediaWiki.
    :rtype: Dict[str, str]
    """
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

    dictionary_of_authorized_users = {k["name"].lower(): True for k in authorized_users}

    return dictionary_of_authorized_users


def verify_user_is_authorized(
    url: str, user_domain: str, session: requests.Session
) -> None:
    """
    Checks if a user is authorised to make changes to the wiki.

    :param url: The URL of the MediaWiki API.
    :type url: str
    :param user_domain: The domain of the user who wants to make changes to the wiki.
    :type user_domain: str
    :param session: A session object used to make requests to the API.
    :type session: requests.Session

    :raises UserNotAuthorized: If the user is not authorised to make changes to the wiki.
    """
    authorized_users = get_list_of_authorized_users(url, session)

    if not authorized_users.get(user_domain.lower()):
        raise UserNotAuthorized


def parse_url(
    content_url: str, csrf_token: str, session: requests.Session
) -> Tuple[Dict[str, Any], str]:
    """
    Retrieves a h-review or h-entry from a URL, checks for a syndication link,
    and makes a dictionary with information that will be used to create the
    new wiki page (or update an existing one).

    :param content_url: The URL of the content to be parsed.
    :type content_url: str
    :param csrf_token_request: A CSRF token retrieved from the MediaWiki API.
    :type csrf_token_request: str
    :return: A tuple containing a dictionary of information about the content for the new wiki page.

    :raises requests.exceptions.RequestException: The request to get the content on a page fails.
    :raises SyndicationLinkNotPresent: The specified URL does not have a syndication link to the MediaWiki instance.
    """
    content_parsed = mf2py.parse(url=content_url)

    h_reviews = []

    for item in content_parsed["items"]:
        item_type = item["type"][0]

        if item_type == "h-review":
            h_reviews.append(item)

        if item_type == "h-entry":
            parsed_entry = mf2py.parse(doc=item["properties"]["content"][0]["html"])

            for new_item in parsed_entry["items"]:
                item_type = new_item["type"][0]

                if item_type == "h-review":
                    h_reviews.append(new_item["properties"])

    domain = urlparse_func(content_url).netloc

    html = ""

    for h_review in h_reviews:
        content_details = parse_h_review(h_review, content_parsed, content_url, domain, h_review["properties"]["name"][0].replace(" - ", " ").replace(" ", "_"))

        html += content_details["content"]["html"]

        submit_edit_request(content_details, session, API_URL, csrf_token)

    h_entry = [e for e in content_parsed["items"] if e["type"][0] == "h-entry" or e["type"][0] == "h-review"]

    if len(h_entry) == 0:
        raise Exception

    h_entry_item = h_entry[0].get("properties")

    if not h_entry_item:
        raise Exception

    categories = [f"[[Category:{c}]]" for c in h_entry_item["category"]]

    # check for syndication link
    # if not h_entry_item.get("syndication"):
    #     raise SyndicationLinkNotPresent

    # if SYNDICATION_LINK not in h_entry_item.get("syndication"):
    #     raise SyndicationLinkNotPresent

    name = h_entry_item.get("name") or ""

    if isinstance(name, list):
        name = name[0]

    content = h_entry_item.get("content") or ""

    if isinstance(content, list):
        content = content[0]

    url = h_entry_item.get("url") or ""

    if isinstance(url, list):
        url = url[0]

    content_details = {
        "name": name,
        "content": content,
        "url": url,
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
    """
    Submits an edit request to the MediaWiki API.

    Edit requests create a new page if the specified page does not exist.

    :param content_details: A dictionary of information about the page to edit.
    :type content_details: Dict[str, str]
    :param session: A session object used to make requests to the API.
    :type session: requests.Session
    :param api_url: The URL of the MediaWiki API.
    :type api_url: str
    :param csrf_token: A CSRF token retrieved from the MediaWiki API.
    :type csrf_token: str

    :raises requests.exceptions.RequestException: The edit request failed.
    """
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
        result = session.post(api_url, data=edit_page_params)
    except requests.exceptions.RequestException as exception:
        raise exception
