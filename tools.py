import pymorphy2
import email.utils
from datetime import datetime

async def format_seconds(seconds, word:str = 'секунда'):
    try:
        morph = pymorphy2.MorphAnalyzer()
        parsed_word = morph.parse(word)[0]
        res = f"{seconds} {parsed_word.make_agree_with_number(seconds).word}"
    except:
        res = "ERROR"
    return res

async def get_name(head:str):
    if head.startswith("attachment; filename="):
        return head.split("attachment; filename=")[-1]
    else:
        return email.utils.unquote(head.split("filename*=utf-8''")[-1])


async def graf(data:list, date_key: str):
    tab = []
    output = {}
    for i in data:
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