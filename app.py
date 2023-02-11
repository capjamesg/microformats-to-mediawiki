from urllib.parse import urlparse as urlparse_func

# from flasgger import Swagger, swag_from
from flask import Flask, Response, jsonify, request, render_template

from config import API_URL, PASSPHRASE
from mediawiki import (SyndicationLinkNotPresent, UserNotAuthorized,
                       get_csrf_token, get_login_token_state, log_in,
                       parse_url, verify_user_is_authorized, update_map_on_category_page)
from hreview import create_map
import requests

app = Flask(__name__)

app.config["SWAGGER"] = {
    "title": "Microformats to MediaWiki API (Breakfast and Coffee)",
    "description": "A Flask API that accepts a URL and turns its h-entry and h-review microformats into a MediaWiki page.",
    "version": "0.1.0",
}

# swagger = Swagger(app)


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        content_details, domain = parse_url(request.form["url"], "", requests.Session, False)
        return render_template("index.html", url=request.form["url"], markup=content_details["content"]["html"])

    return render_template("index.html")


@app.route("/webhook", methods=["POST"])
# @swag_from("docs/webhook.yml")
def submit_post():
    # passphrase = request.args.get("passphrase")

    # if passphrase != PASSPHRASE:
    #     return jsonify({"error": "user not authorised"}), 403

    # if request.json is None:
    #     return jsonify({"error": "invalid request body"}), 400

    request_body = request.json.get("post")

    if request_body is None:
        return jsonify({"error": "invalid request body"}), 400

    url_to_parse = request_body.get("url", "")

    # get url from query string
    # url_to_parse = request.args.get("url")

    if url_to_parse == "":
        return jsonify({"error": "invalid request body"}), 400

    domain = urlparse_func(url_to_parse).netloc

    token_request, session = get_login_token_state(API_URL)

    log_in(API_URL, token_request, session)

    csrf_token_request = get_csrf_token(API_URL, session)

    # user must be on approved list of domains
    try:
        verify_user_is_authorized(API_URL, domain, session)
    except UserNotAuthorized:
        return jsonify({"error": "user not authorised"}), 403

    # try:
    parse_url(url_to_parse, csrf_token_request, session)
    # except SyndicationLinkNotPresent:
    #     return jsonify({"error": "syndication link not present"}), 400

    # set Location header
    response = Response(status=201)
    response.headers["Location"] = url_to_parse

    return response

@app.route("/map")#, methods=["POST"])
# @swag_from("docs/map.yml")
def map():
    coordinates = request.args.get("coordinates")

    coordinate_list = coordinates.split("|")

    coordinate_lists = [coordinate.split(",") for coordinate in coordinate_list]

    coordinate_lists = [[float(coordinate) for coordinate in coordinate_list] for coordinate_list in coordinate_lists]

    return render_template("mapindex.html", coordinates=coordinate_lists)

@app.route("/map/update")
def update_map():
    update_map_on_category_page("Leeds")

    return ""