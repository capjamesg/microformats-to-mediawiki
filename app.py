from urllib.parse import urlparse as urlparse_func

from flask import Flask, abort, jsonify, request

from config import API_URL, PASSPHRASE
from mediawiki import (
    SyndicationLinkNotPresent,
    UserNotAuthorized,
    get_csrf_token,
    get_login_token_state,
    log_in,
    parse_url,
    submit_edit_request,
    verify_user_is_authorized,
)

app = Flask(__name__)


@app.route("/webhook", methods=["GET", "POST"])
def submit_post():
    passphrase = request.args.get("passphrase")

    if passphrase != PASSPHRASE:
        abort(403)

    url_to_parse = request.json.get("post", {}).get("url", "")

    domain = urlparse_func(url_to_parse).netloc

    if url_to_parse == "":
        abort(400)

    token_request, session = get_login_token_state(API_URL)

    log_in(API_URL, token_request, session)

    csrf_token_request = get_csrf_token(API_URL, session)

    # user must be on approved list of domains
    try:
        verify_user_is_authorized(API_URL, domain, session)
    except UserNotAuthorized:
        return abort(403)

    try:
        content_details, csrf_token = parse_url(
            url_to_parse,
            csrf_token_request,
        )

        submit_edit_request(content_details, session, API_URL, csrf_token)
    except SyndicationLinkNotPresent as e:
        abort(400)

    return jsonify({"success": True}), 200
