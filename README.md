# ruccola

> Terminal-based client for rocket.chat

## Installation

`ruccola` is written in Python (3.5+).

The requirements are listed in `requirements.txt`.

Once all dependencies are installed and the
configuration file has been created (see below),
the client can be launched using:


        python3 -m libruccola


...or installed using `setup.py`.

## Usage

To use the client, you have to generate a Personal Access Token
from the Security options in the rocket.chat web UI. If you don't
see the option to do that, the administrator has not enabled this
feature.

Once generated, put the token and user ID in
`~/.config/ruccola/config.ini` like this:

```
[auth]
server = chat.example.com
user_id = abc123...
token = abc123...
```

With that you should be able to start the client.

