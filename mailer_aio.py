#!/usr/bin/env python3

import urllib.request, base64, codecs, re, os, sys, pickle

clone = []
counts = {}
remote_counts = {}
full = False
h = False
features = []
ue = False
xc = False
to = False
depth = "200"

def load_config():
    node = ""
    depth = "200"
    echoareas = []
    auth = False
    nodename = "unknown"
    f = open(config, "r").read().split("\n")
    for line in f:
        param = line.split(" ")
        if param[0] == "node":
            node = param[1]
        elif param[0] == "nodename":
            nodename = param[1:]
        elif param[0] == "auth":
            auth = param[1]
        elif param[0] == "depth":
            depth = param[1]
        elif param[0] == "echo":
            echoareas.append(param[1])
    return node, nodename, auth, depth, echoareas

def check_directories():
    if not os.path.exists("aio"):
        os.makedirs("aio")

def make_toss():
    lst = [x for x in os.listdir("out/" + nodename) if x.endswith(".out")]
    for msg in lst:
        text = codecs.open("out/" + nodename + "/%s" % msg, "r", "utf-8").read()
        coded_text = base64.b64encode(text.encode("utf-8"))
        codecs.open("out/" + nodename + "/%s.toss" % msg, "w", "utf-8").write(coded_text.decode("utf-8"))
        os.rename("out/" + nodename + "/%s" % msg, "out/" + nodename + "/%s%s" % (msg, "msg"))

def send_mail():
    lst = [x for x in sorted(os.listdir("out/" + nodename)) if x.endswith(".toss")]
    max = len(lst)
    n = 1
    try:
        for msg in lst:
            print("\rОтправка сообщения: " + str(n) + "/" + str(max), end="")
            text = codecs.open("out/" + nodename + "/%s" % msg, "r", "utf-8").read()
            data = urllib.parse.urlencode({"tmsg": text,"pauth": auth}).encode("utf-8")
            request = urllib.request.Request(node + "u/point")
            result = urllib.request.urlopen(request, data).read().decode("utf-8")
            if result.startswith("msg ok"):
                os.remove("out/" + nodename + "/%s" % msg)
                n = n + 1
            elif result == "msg big!":
                print("\nERROR: very big message (limit 64K)!")
            elif result == "auth error!":
                print("\nERROR: unknown auth!")
            else:
                print("\nERROR: unknown error!")
        if len(lst) > 0:
            print()
    except:
        print("\nОшибка: не удаётся связаться с нодой.")

def separate(l, step=40):
    for x in range(0, len(l), step):
        yield l[x:x+step]

def get_features():
    global features
    try:
        r = urllib.request.Request(node + "x/features")
        with urllib.request.urlopen(r) as f:
            features = f.read().decode("utf-8").split("\n")
    except:
        features = []

def check_features():
    global ue, xc
    ue = "u/e" in features
    xc = "x/c" in features

def load_counts():
    global counts
    if os.path.exists("counts.lst"):
        f = open("counts.lst", "rb")
        counts = pickle.load(f)
        f.close()
    else:
        counts[node] = {}
    if not node in counts:
        counts[node] = {}

def save_counts():
    counts[node] = remote_counts
    f = open("counts.lst", "wb")
    pickle.dump(counts, f)
    f.close()

def get_remote_counts():
    counts = {}
    r = urllib.request.Request(node + "x/c/" + "/".join(echoareas))
    with urllib.request.urlopen(r) as f:
        c = f.read().decode("utf-8").split("\n")
    for count in c:
        echoarea = count.split(":")
        if len(echoarea) > 1:
            counts[echoarea[0]] = echoarea[1]
    return counts

def calculate_offset():
    global depth
    n = False
    offset = 0
    for echoarea in echoareas:
        if not echoarea in counts[node]:
            n = True
        else:
            if not echoarea in clone and int(remote_counts[echoarea]) - int(counts[node][echoarea]) > offset:
                offset = int(remote_counts[echoarea]) - int(counts[node][echoarea])
    if not n:
        depth = offset

def get_echoarea(echo):
    if os.path.exists("aio/" + echo + ".aio"):
        f = codecs.open("aio/" + echo + ".aio", "r", "utf-8").read().split("\n")
        msgids = []
        for line in f:
            if len(line) > 0:
                msgids.append(line.split(":")[0])
    else:
        msgids = []
    return msgids

def get_msg_list():
    global clone
    msg_list = []
    fetch_echoareas = []
    if not full and ue:
        for echoarea in echoareas:
            if not echoarea in clone and (not echoarea in counts[node] or int(counts[node][echoarea]) < int(remote_counts[echoarea])):
                fetch_echoareas.append(echoarea)
    else:
        clone = echoareas
    if len(clone) > 0:
        r = urllib.request.Request(node + "u/e/" + "/".join(clone))
        with urllib.request.urlopen(r) as f:
            lines = f.read().decode("utf-8").split("\n")
            for line in lines:
                if len(line) > 0:
                    msg_list.append(line)
    if len(fetch_echoareas) > 0 and int(depth) > 0:
        r = urllib.request.Request(node + "u/e/" + "/".join(fetch_echoareas) + "/-%s:%s" %(depth, depth))
        with urllib.request.urlopen(r) as f:
            lines = f.read().decode("utf-8").split("\n")
            for line in lines:
                if len(line) > 0:
                    msg_list.append(line)
    return msg_list

def get_bundle(node, msgids):
    bundle = []
    r = urllib.request.Request(node + "u/m/" + msgids)
    with urllib.request.urlopen(r) as f:
        bundle = f.read().decode("utf-8").split("\n")
    return bundle

def get_carbonarea():
    try:
        f = open("aio/carbonarea.aio", "r").read().split("\n")
        carbonarea = []
        for line in f:
            carbonarea.append(line.split(":")[0])
        return carbonarea
    except:
        return []

def add_to_carbonarea(msgid, msgbody):
    codecs.open("aio/carbonarea.aio", "a", "utf-8").write(msgid + ":" + chr(15).join(msgbody) + "\n")

def debundle(bundle):
    for msg in bundle:
        if msg:
            m = msg.split(":")
            msgid = m[0]
            if len(msgid) == 20 and m[1]:
                msgbody = base64.b64decode(m[1].encode("ascii")).decode("utf8").split("\n")
                codecs.open("aio/" + msgbody[1] + ".aio", "a", "utf-8").write(msgid + ":" + chr(15).join(msgbody) + "\n")
                if to:
                    carbonarea = get_carbonarea()
                    if msgbody[5] in to and not msgid in carbonarea:
                        add_to_carbonarea(msgid, msgbody)

def echo_filter(ea):
    rr = re.compile(r'^[a-z0-9_!.-]{1,60}\.[a-z0-9_!.-]{1,60}$')
    if rr.match(ea): return True

def get_mail():
    fetch_msg_list = []
    print("Получение индекса от ноды...")
    remote_msg_list = get_msg_list()
    print("Построение разностного индекса...")
    local_index = []
    for line in remote_msg_list:
        if echo_filter(line):
            if line in clone and ue:
                try:
                    os.remove("aio/" + line + ".aio")
                except:
                    None
            local_index = get_echoarea(line)
        else:
            if not line in local_index:
                fetch_msg_list.append(line)
    msg_list_len = str(len(fetch_msg_list))
    if len(fetch_msg_list) > 0:
        count = 0
        for get_list in separate(fetch_msg_list):
            count = count + len(get_list)
            print("\rПолучение сообщений: " + str(count) + "/"  + msg_list_len, end="")
            debundle(get_bundle(node, "/".join(get_list)))
    else:
        print("Новых сообщений не обнаружено.", end="")
    print()

def check_new_echoareas():
    local_base = os.listdir("echo/")
    n = False
    for echoarea in echoareas:
        if not echoarea in local_base:
            n = True
    return n

def show_help():
    print("Usage: mailer_aio.py [-f filename] [-n node] [-e echoarea1,echoarea2,...] [-d depth] [-c echoarea1,echoarea2,...] [-o] [-to name1,name2...] [-h].")
    print()
    print("  -f filename  load config file. Default idec-fetcher.cfg.")
    print("  -n node      node address.")
    print("  -m nodename  nodename for search .out messages.")
    print("  -a authkey   authkey.")
    print("  -e echoareas echoareas for fetch.")
    print("  -d depth     fetch messages with an offset to a predetermined depth. Default 200.")
    print("  -c echoareas clone echoareas from node.")
    print("  -o           old mode. Get full index from nore.")
    print("  -to names    names for put messages to carbonarea.")
    print("  -h           this message.")
    print()
    print("If -f not exist, script will load config from current directory with name\nfetcher.cfg.")

args = sys.argv[1:]

conf = "-f" in args
if conf:
    config = args[args.index("-f") + 1]
else:
    config = "fetcher.cfg"
if "-c" in args:
    clone = args[args.index("-c") + 1].split(",")
full = "-o" in args
if "-d" in args:
    depth = args[args.index("-d") + 1]
h = "-h" in args
if "-n" in args:
    node = args[args.index("-n") + 1]
if "-m" in args:
    nodename = args[args.index("-m") + 1]
if "-a" in args:
    auth = args[args.index("-a") + 1]
if "-e" in args:
    echoareas = args[args.index("-e") + 1].split(",")
if "-to" in args:
    to = args[args.index("-to") + 1].split(",")
wait = "-w" in args

if h:
    show_help()
    quit()

if not "-n" in args and not "-e" in args and not os.path.exists(config):
    print("Config file not found.")
    quit()

check_directories()
if not "-n" in args or not "-e" in args:
    node, nodename, auth, depth, echoareas = load_config()
print("Работа с " + node)
make_toss()
send_mail()
print("Получение списка возможностей ноды...")
if auth:
    get_features()
    check_features()
if xc:
    load_counts()
    print("Получение количества сообщений в конференциях...")
    remote_counts = get_remote_counts()
    calculate_offset()
get_mail()
if xc:
    save_counts()
if wait:
    input("Нажмите Enter для продолжения.")
    print()