# Publish a microformats h-entry to MediaWiki

This repository contains a script and web server to publish a microformats h-entry to MediaWiki.

This project is being used on the [Breakfast and Coffee](https://breakfastand.coffee) to allow wiki submissions from other websites.

## Getting Started

First, install the required dependencies for this project:

    python3 -r requirements.txt

Then, create a config.py file with the following variables:

    PASSPHRASE="the unique password you want to use to access the webhook"
    LGNAME="your bot username for the wiki you are using"
    LGPASSWORD="your bot password for the wiki you are using"
    SYNDICATION_LINK="your wiki URL"
    API_URL="the URL of your wiki api.php file"
    
You can get the LGNAME and LGPASSWORD values using the [Bot passwords](https://www.mediawiki.org/wiki/Manual:Bot_passwords) MediaWiki feature.

Finally, run the web server:

    python3 wsgi.py

The web server creates an endpoint at /webhook where you can send POST requests.

The endpoint looks for a payload from [webmention.io](https://webmention.io), which is being used to host the [Breakfast and Coffee](https://breakfastand.coffee) Webmention endpoint.

You can change the "url_to_parse" variable to change the way in which the URL to parse is retrieved, depending on how you want your webhook to work.

## Technologies

- Python
- Flask

## License

This project is licensed under the [MIT license](LICENSE).

## Contributors

- capjamesg