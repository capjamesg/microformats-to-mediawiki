import datetime

from jinja2 import Template


def parse_h_recipe(h_recipe: dict, domain: str) -> str:
    """
    Parse a h-recipe microformat into a MediaWiki page.

    :param h_recipe: A dictionary containing the h-recipe microformat
    :param domain:Tthe domain of the URL that the h-recipe microformat was found on
    :returns: A dictionary containing the name of the recipe and the MediaWiki page content
    :rtype: dict
    """
    with open("wiki_templates/recipe.html", "r") as f:
        template = Template(f.read())

    # get the recipe name
    name = h_recipe["properties"]["name"][0] if "name" in h_recipe["properties"] else ""
    results_yield = (
        h_recipe["properties"]["yield"][0] if "yield" in h_recipe["properties"] else ""
    )
    duration = (
        h_recipe["properties"]["duration"][0]
        if "duration" in h_recipe["properties"]
        else ""
    )
    results_ingredients = (
        h_recipe["properties"]["ingredient"]
        if "ingredient" in h_recipe["properties"]
        else []
    )
    results_instructions = (
        h_recipe["properties"]["instructions"][0]
        if "instructions" in h_recipe["properties"]
        else []
    )
    photo = (
        h_recipe["properties"]["photo"][0] if "photo" in h_recipe["properties"] else ""
    )
    url = h_recipe["properties"]["url"][0] if "url" in h_recipe["properties"] else ""

    rendered_page = template.render(
        name=name,
        results_yield=results_yield,
        duration=duration,
        ingredients=results_ingredients,
        instructions=results_instructions,
        photo=photo,
        domain=domain,
        date=datetime.datetime.now().strftime("%Y-%m-%d"),
        url=url,
    )

    # add [Category:Recipes] to the end of the page
    rendered_page += "\n\n[[" + "Category:Recipes]]"

    content_details = {
        "name": name,
        "content": {"html": rendered_page},
        "url": "https://breakfastand.coffee/" + name,
    }

    return content_details
