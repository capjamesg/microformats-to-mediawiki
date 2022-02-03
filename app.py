from flask import Flask, request, abort

from mediawiki import (
    get_csrf_token,
    get_login_token_state,
    log_in,
    parse_url,
    submit_edit_request,
    SyndicationLinkNotPresent
)

from config import PASSPHRASE, API_URL

app = Flask(__name__)


@app.route("/webhook", methods=["POST"])
def submit_post():
    passphrase = request.args.get("passphrase")

    if passphrase != PASSPHRASE:
        abort(403)

    url_to_parse = request.json.get("post", {}).get("url", "")

    if url_to_parse == "":
        abort(400)

    token_request, session = get_login_token_state(
        API_URL
    )

    log_in(API_URL, token_request, session)
    
    csrf_token_request = get_csrf_token(API_URL, session)

    try:
        content_details, csrf_token = parse_url(
            url_to_parse,
            csrf_token_request,
        )

        submit_edit_request(
            content_details, session, API_URL, csrf_token
        )
    except SyndicationLinkNotPresent as e:
        return abort(400)

    return 200