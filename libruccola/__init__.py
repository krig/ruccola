from libruccola import config, api

def main():
    cfg = config.parse()
    session = api.Session(cfg)
    
    print("Joined channels:\n")
    for channel in session.listJoinedChannels():
        print("#{}".format(channel.name))

