import random
import requests
from bs4 import BeautifulSoup, element


def get_shindan_link():
    url: str = "https://shindanmaker.com/list/pickup"

    headers: dict[str, str] = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
    }

    response: requests.models.Response = requests.get(url, headers=headers, timeout=30)

    if response.status_code != 200:
        return None

    html: bytes = response.content
    soup: BeautifulSoup = BeautifulSoup(html, "html.parser")
    shindan_links: element.ResultSet = soup.find_all("a", class_="shindanLink")

    if len(shindan_links) == 0:
        return

    shindan_link: element.Tag = random.choice(shindan_links)
    link: str = shindan_link.get("href")
    return link
