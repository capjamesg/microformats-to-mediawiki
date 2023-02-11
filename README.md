# Publish a microformats h-entry to MediaWiki

This repository contains a script and web server to publish a microformats h-entry to MediaWiki.

This project is being used on the [Breakfast and Coffee](https://breakfastand.coffee) to allow wiki submissions from other websites.

## Getting Started

First, install the required dependencies for this project:

    pip3 -r requirements.txt

Then, create a config.py file with the following variables:

    PASSPHRASE="the unique password you want to use to access the webhook"
    LGNAME="your bot username for the wiki you are using"
    LGPASSWORD="your bot password for the wiki you are using"
    SYNDICATION_LINK="your wiki URL"
    API_URL="the URL of your wiki api.php file"
    REQUIRE_SYNDICATION_LINK=False
    
You can get the LGNAME and LGPASSWORD values using the [Bot passwords](https://www.mediawiki.org/wiki/Manual:Bot_passwords) MediaWiki feature.

If `REQUIRE_SYNDICATION_LINK` is set to `True`, the API will only accept posts that have a syndication link to the wiki homepage. This is useful if you want to ensure that only posts that are syndicated to your wiki are added to the wiki. If you set this to `False`, the API will accept any post that has a valid URL and the right markup.

Finally, run the web server:

    python3 wsgi.py

The web server creates an endpoint at /webhook where you can send POST requests.

The endpoint looks for a payload from [webmention.io](https://webmention.io), which is being used to host the [Breakfast and Coffee](https://breakfastand.coffee) Webmention endpoint.

You can change the "url_to_parse" variable to change the way in which the URL to parse is retrieved, depending on how you want your webhook to work.

### Type checking and linting

You can run a type check and lint on this codebase using the following command:

    tox

## API Documentation

This API contains a single endpoint that creates a wiki page for a user.

## Authentication

To use this API, you need to specify a `?passphrase=` URL argument. The value of this argument should be equal to the `PASSPHRASE` value you set in your `config.py` file.

### Create a wiki page

To create a wiki page, you must be registered with the MediaWiki associated with the installation of this software. Your MediaWiki username must be equal to the domain from which you want to post a URL. This ensures that you cannot submit an arbitrary post to the wiki that you do not own.

Request syntax:

```
GET /webhook?passphrase=[passphrase]
Content-Type: application/json

Request Body:

{
    "post": {
        "url": "https://example.com"
    }
}

```

The body of your request should include the URL of the post you want to add to the wiki. The post must be marked up with either [h-entry](https://microformats.org/wiki/h-entry) or [h-review](https://microformats.org/wiki/h-review) microformats. A response from the [webmention.io](https://webmention.io) webhook feature is compatible with the API.

If the post is a h-review, your post will be created as a review page on the wiki. If a page already exists for the place you want to review, your review will be appended to the existing page.

h-entry posts are created as regular wiki entries.

This endpoint may return the following status codes:

- `403`: A valid passphrase was not specified or the domain who created the post is not registered as a user on the wiki.
- `400`: A valid post URL was not specified or a syndication link was not present.
- `201`: Your post was created successfully. A 201 response will send a `Location: ` header that contains the URL of the post created on the MediaWiki.

All edits are made in the name of the bot user specified in your configuration file.

## Technologies

- Python
- Flask

## License

This project is licensed under the [MIT 0 license](LICENSE).

## Contributors

- capjamesg