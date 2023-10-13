import pymorphy2
import email.utils
from urllib.parse import urlparse
from urllib.parse import parse_qs
from datetime import datetime


# Пункты, которые игнорируем
graphs_ignore = [
    "/statistics/info/type_map/",
    "/statistics/info/all/",
    "/statistics/delay/",
    "/statistics/hour/",
    "/statistics/day/",
    "/info/queue/size",
    "/download/steam/",
    "mod_not_found_local",
    "/condition/mod/",
    "/update/steam/",
    "/list/tags/"
    "/list/mods/",
    "/download/",
    "start",
    "/"
]

async def pars_link(link):
    if link.startswith("https://steamcommunity.com/sharedfiles/filedetails/") or link.startswith(
                       "https://steamcommunity.com/workshop/filedetails/") or link.startswith(
                       "https://openworkshop.su/mod/"):
        parsed = urlparse(link, "highlight=params#url-parsing")

        try:
            if parsed.path.startswith("/mod/"):
                link = parsed.path.removeprefix("/mod/")
            else:
                captured_value = parse_qs(parsed.query)
                link = captured_value['id'][0]
        except:
            link = False
    return link

async def format_seconds(seconds, word: str = 'секунда') -> str:
    try:
        morph = pymorphy2.MorphAnalyzer()
        parsed_word = morph.parse(word)[0]
        res = f"{seconds} {parsed_word.make_agree_with_number(seconds).word}"
    except:
        res = "ERROR"
    return res

async def get_name(head: str) -> str:
    if head.startswith("attachment; filename="):
        return head.split("attachment; filename=")[-1]
    else:
        return email.utils.unquote(head.split("filename*=utf-8''")[-1])


async def graf(data: list, date_key: str) -> list[dict, list]:
    tab = []
    output = {}
    for i in data:
        if i["type"] not in graphs_ignore:
            if not output.get(i["type"]):
                output[i["type"]] = [[], []]

            output[i["type"]][1].append(i["count"])

            if date_key == "date_time":
                output[i["type"]][0].append(datetime.fromisoformat(i[date_key]).hour)
            elif date_key == "date":
                output[i["type"]][0].append(datetime.fromisoformat(i[date_key]).toordinal())
                if datetime.fromisoformat(i[date_key]) not in tab:
                    tab.append(datetime.fromisoformat(i[date_key]))

    return [output, tab]
