import pymorphy2
import email.utils

async def format_seconds(seconds):
    try:
        morph = pymorphy2.MorphAnalyzer()
        word = 'секунда'
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
