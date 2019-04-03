from libruccola import config, api
from prompt_toolkit.eventloop import use_asyncio_event_loop
import asyncio

COLORS = [
    'ansired', 'ansigreen', 'ansiyellow', 'ansiblue', 'ansifuchsia',
    'ansiturquoise', 'ansilightgray', 'ansidarkgray', 'ansidarkred',
    'ansidarkgreen', 'ansibrown', 'ansidarkblue', 'ansipurple', 'ansiteal']


class AppState(object):
    def __init__(self, app, mainbuf, inbuf, chanbuf):
        self.app = app
        self.mainbuf = mainbuf
        self.inbuf = inbuf
        self.chanbuf = chanbuf
        self.cached_channels = {}

def build_layout(rchat):
    from prompt_toolkit.application import Application
    from prompt_toolkit.buffer import Buffer
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.layout.containers import VSplit, HSplit, Window, WindowAlign
    from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
    from prompt_toolkit.layout.layout import Layout
    from prompt_toolkit.styles import Style
    from prompt_toolkit import prompt
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
            style=style,
            full_screen=True)
    appstate = AppState(app, mainbuf, inbuf, chanbuf)
    return app, appstate

def list_channels(rchat, appstate):
    channels = rchat.listJoinedChannels()
    for channel in channels:
        appstate.cached_channels[channel.name] = channel
    s = " ".join("#{}".format(channel.name) for channel in channels)
    appstate.chanbuf.text = s

def main():
    cfg = config.parse()
    rchat = api.Session(cfg)
    app, appstate = build_layout(rchat)
    use_asyncio_event_loop()
    loop = asyncio.get_event_loop()
    loop.call_soon(list_channels, rchat, appstate)
    loop.run_until_complete(app.run_async().to_asyncio_future())
