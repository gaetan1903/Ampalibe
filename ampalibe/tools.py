import os
import pickle
import inspect
import asyncio
from .cmd import Cmd
from .messenger import Messenger

funcs = {
    "command": {},
    "action": {},
    "event": {},
    "before": None,
    "after": None,
}


async def verif_func(func, **kwargs):
    """
    function verify if the function is a coroutine or not before running it
    """
    return await func(**kwargs) if inspect.iscoroutinefunction(func) else func(**kwargs)


def analyse(data):
    """
    Function analyzing data received from Facebook
    The data received are of type Json .
    """

    for event in data["entry"]:
        messaging = event["messaging"]

        for message in messaging:

            sender_id = message["sender"]["id"]

            if message.get("message"):

                if message["message"].get("attachments"):
                    # Get file name
                    data = message["message"].get("attachments")
                    # creation de l'objet cmd personalisé
                    atts = list(map(lambda dt: dt["payload"]["url"], data))
                    cmd = Cmd(atts[0])
                    cmd.set_atts(atts)
                    cmd.webhook = "attachments"
                    return sender_id, cmd, message
                elif message["message"].get("quick_reply"):
                    # if the response is a quick reply
                    return (
                        sender_id,
                        Cmd(message["message"]["quick_reply"].get("payload")),
                        message,
                    )
                elif message["message"].get("text"):
                    # if the response is a simple text
                    return (
                        sender_id,
                        Cmd(message["message"].get("text")),
                        message,
                    )

            if message.get("postback"):
                recipient_id = sender_id
                pst_payload = Cmd(message["postback"]["payload"])
                pst_payload.webhook = "postback"
                return recipient_id, pst_payload, message

            if message.get("read"):
                watermark = Cmd(message["read"].get("watermark"))
                watermark.webhook = "read"
                return sender_id, watermark, message

            if message.get("delivery"):
                watermark = Cmd(message["delivery"].get("watermark"))
                watermark.webhook = "delivery"
                return sender_id, watermark, message

            if message.get("reaction"):
                reaction = Cmd(message["reaction"].get("reaction"))
                reaction.webhook = "reaction"
                return sender_id, reaction, message

            if message.get("optin"):
                optin = Cmd(message["optin"]["payload"])
                optin.webhook = "optin"
                if message["optin"].get("type") == "one_time_notif_req":
                    optin.token = message["optin"]["one_time_notif_token"]
                elif message["optin"].get("type") == "notification_messages":
                    optin.token = message["optin"]["notification_messages_token"]
                return sender_id, optin, message

    return None, Cmd(""), None


async def before_run(func, **kwargs):
    """
    Function to be executed before running the function
    called by the user command
    """

    res = None
    if funcs["before"] and hasattr(funcs["before"], "__call__"):
        if await verif_func(funcs["before"], **kwargs):
            res = await verif_func(func, **kwargs)
    else:
        res = await verif_func(func, **kwargs)

    if funcs["after"] and hasattr(funcs["after"], "__call__"):
        kwargs["res"] = res
        await verif_func(funcs["after"], **kwargs)

    return res


def send_next(sender_id, payload):
    chat = Messenger()
    if os.path.isfile(f"assets/private/.__{sender_id}"):
        elements = pickle.load(open(f"assets/private/.__{sender_id}", "rb"))
        if payload == "/__next":
            chat.send_generic_template(sender_id, elements[0], next=elements[1])
        else:
            chat.send_quick_reply(sender_id, elements[0], elements[1], next=elements[2])


async def verif_event(testmode, payload, sender_id, message):
    if funcs["event"].get(payload.webhook):
        kw = {
            "sender_id": sender_id,
            "watermark": payload,
            "message": message,
        }
        if testmode:
            await verif_func(funcs["event"][payload.webhook], **kw)
        else:
            asyncio.create_task(verif_func(funcs["event"][payload.webhook], **kw))