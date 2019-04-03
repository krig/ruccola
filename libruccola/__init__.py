from libruccola import config, api
from prompt_toolkit.eventloop import use_asyncio_event_loop
import asyncio

COLORS = [
    'ansired', 'ansigreen', 'ansiyellow', 'ansiblue', 'ansifuchsia',
    'ansiturquoise', 'ansilightgray', 'ansidarkgray', 'ansidarkred',
    'ansidarkgreen', 'ansibrown', 'ansidarkblue', 'ansipurple', 'ansiteal']


_df = open("ruccola.log", "a")
def dlog(msg):
    _df.write("{}\n".format(msg))
    _df.flush()


class AppState(object):
    def __init__(self, app, mainbuf, inbuf, chanbuf):
        self.app = app
        self.mainbuf = mainbuf
        self.inbuf = inbuf
        self.chanbuf = chanbuf
        self.cached_channels = {}
        self.active_channel = None

def build_layout(rchat):
    from prompt_toolkit.application import Application
    from prompt_toolkit.buffer import Buffer
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.layout.containers import VSplit, HSplit, Window, WindowAlign
    from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
    from prompt_toolkit.layout.layout import Layout
    from prompt_toolkit.styles import Style
    from prompt_toolkit import prompt
    from prompt_toolkit.completion import WordCompleter

    cmd_completer = WordCompleter([
        '/list',
        '/win',
        '/search',
        '/msg',
    ])

    mainbuf = Buffer()
    mainwin = Window(BufferControl(buffer=mainbuf))
    def get_titlebar_text():
        return [
            ('class:title', ' {} '.format(rchat.config.server)),
            ('class:title', ' (Press [C-Q] to quit.)'),
        ]
    inbuf = Buffer()
    inwin = Window(BufferControl(buffer=inbuf), height=1)
    chanbuf = Buffer()
    channels = Window(BufferControl(buffer=chanbuf), height=1, style='class:status')
    root = HSplit([
        # Titlebar
        Window(height=1,
            content=FormattedTextControl(get_titlebar_text),
            align=WindowAlign.CENTER),
        mainwin,
        channels,
        inwin
    ])
    kb = KeyBindings()

    @kb.add('c-c', eager=True)
    @kb.add('c-q', eager=True)
    def _(event):
        event.app.exit()

    def onbufferchange(_):
        mainbuf.text = inbuf.text[::-1]

    inbuf.on_text_changed += onbufferchange
    
    style = Style.from_dict({
        'title': 'reverse',
        'status': 'bg:ansiblack fg:ansibrightgreen',
        'shadow': 'bg:ansiblue',
    })

    app = Application(
            layout=Layout(root, focused_element=inwin),
            key_bindings=kb,
            enable_page_navigation_bindings=True,
            style=style,
            full_screen=True)
    appstate = AppState(app, mainbuf, inbuf, chanbuf)
    return app, appstate


def get_history(loop, rchat, appstate):
    if appstate.active_channel is None:
        return
    ch = appstate.active_channel
    messages = ch.history()
    dlog(repr(messages))
    lines = []
    for msg in messages:
        lines.append("@{}: {}".format(msg["u"]["username"], msg["msg"]))
    lines.reverse()
    appstate.mainbuf.text = "\n".join(lines)

def list_channels(loop, rchat, appstate):
    channels = rchat.listJoinedChannels()
    for channel in channels:
        if appstate.active_channel is None and channel.name == "clientdev":
            appstate.active_channel = channel
        appstate.cached_channels[channel.name] = channel
    if appstate.active_channel is None:
        appstate.active_channel = appstate.cached_channels.values()[0]
    def fmt(i, name):
        if name == appstate.active_channel.name:
            return "[{}:#{}]".format(i+1, name)
        return "{}:#{}".format(i+1, name)
    s = " ".join(fmt(i, channel.name) for i, channel in enumerate(channels))
    appstate.chanbuf.text = s
    loop.call_soon(get_history, loop, rchat, appstate)


def main():
    cfg = config.parse()
    rchat = api.Session(cfg)
    app, appstate = build_layout(rchat)
    use_asyncio_event_loop()
    loop = asyncio.get_event_loop()
    loop.call_soon(list_channels, loop, rchat, appstate)
    loop.run_until_complete(app.run_async().to_asyncio_future())
