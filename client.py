import threading
import os.path as pt
import shutil
import sys
import time
import tempfile
import libtorrent as lt
import socket

# global stuff
report = ""
state = "idle"

def convert(link, tmp_file):
    tempdir = tempfile.mkdtemp()
    ses = lt.session()
    params = {
        'save_path': tempdir,
        'storage_mode': lt.storage_mode_t(2),
        'paused': False,
        'auto_managed': True,
        'duplicate_is_error': True
        }
    handle = lt.add_magnet_uri(ses, link, params)

    print("Downloading Metadata (this may take a while)")
    while not handle.has_metadata():
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            ses.pause()
            shutil.rmtree(tempdir)
            sys.exit(0)
    ses.pause()
    print("Metadata finished")

    torinfo = handle.get_torrent_info()
    torfile = lt.create_torrent(torinfo)
    output = pt.abspath(torinfo.name() + ".torrent")

    if tmp_file:
        if pt.isdir(tmp_file):
            output = pt.abspath(pt.join(tmp_file, torinfo.name() + ".torrent"))
        elif pt.isdir(pt.dirname(pt.abspath(tmp_file))):
            output = pt.abspath(tmp_file)

    print("Saving torrent file here " + output + " ...")
    torcontent = lt.bencode(torfile.generate())
    f = open(output, "wb")
    f.write(lt.bencode(torfile.generate()))
    f.close()
    print("Saved! Cleaning up dir: " + tempdir)
    ses.remove_torrent(handle)
    shutil.rmtree(tempdir)
    return output

def download(f):
    global report
    global state
    print("downloading")
    ses = lt.session()
    ses.listen_on(6881, 6891)

    info = lt.torrent_info(f)
    h = ses.add_torrent({'ti': info, 'save_path': './downloads/'})

    while (not h.is_seed()):
        s = h.status()
        state_str = ['queued', 'checking', 'downloading metadata', \
                'downloading', 'finished', 'seeding', 'allocating', 'checking fastresume']

        progress = round(s.progress * 100, 2)
        d_rate = s.download_rate / 1000
        u_rate = s.upload_rate / 1000
        peers_count = s.num_peers
        state = state_str[s.state]

        report = "complete: {0} %, down: {1} kB/s, up: {2} kB/s, peers: {3}, state: {4}" .format(progress, d_rate, u_rate, peers_count, state)
        print(report)
        time.sleep(1)

    print("Done!")
    report = ""
    state = "idle"
    time.sleep(3)

def connect():
    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    serversocket.bind(('', 9999))
    serversocket.listen(5)
    (clientsocket, _) = serversocket.accept()
    return clientsocket

def torrent(link, tmp_file="torrent_tmp"):
    f = convert(link, tmp_file)
    download(f)

def pipe_message(message, sock):
    global state
    if message == "state":
        send(state, sock)
    if message == "progress":
        send(report, sock)
    elif message.startswith("magnet:?"):
        state = "running"
        t = threading.Thread(target=torrent, args=(message,))
        t.start()

def send(message, sock):
    sock.send(message + "\n")


sock = connect()
print("rdy")
while True:
    print("waiting for message")
    try:
        message = sock.recv(1024)
        pipe_message(message, sock)
    except KeyboardInterrupt:
        sock.close()
