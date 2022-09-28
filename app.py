from urllib.parse import urlparse as urlparse_func

from flask import Flask, Response, abort, jsonify, request

from config import API_URL, PASSPHRASE
from mediawiki import (SyndicationLinkNotPresent, UserNotAuthorized,
                       get_csrf_token, get_login_token_state, log_in,
                       parse_url, submit_edit_request,
                       verify_user_is_authorized)

app = Flask(__name__)


@app.route("/")
def index():
    return jsonify({})


@app.route("/webhook", methods=["POST"])
def submit_post():
    passphrase = request.args.get("passphrase")

    if passphrase != PASSPHRASE:
        abort(403)

    if request.json is None:
        abort(400)

    url_to_parse = request.json.get("post")
    
    if url_to_parse is None:
        abort(400)
    
    url_to_parse = url_to_parse.get("url", "")

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
    except SyndicationLinkNotPresent:
        abort(400)

    # set Location header
    response = Response(status=201)
    response.headers["Location"] = url_to_parse

    return response
