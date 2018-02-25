import libtorrent as lt
from Queue import Queue
import tempfile
import socket
import shutil
import os.path as pt
import time
import threading
import sys

class Torrent():
    def __init__(self):
        print "start Consumer.."

    def send(self, socket, message):
        socket.send(message + "\n")

    def start(self, clientsocket, message):
        if message.startswith("magnet:?"):
            f = self.convert(message, clientsocket, "torrent_tmp")
            self.download(f, clientsocket)
        else:
            send(clientsocket, "Broken Magnet!")

    def convert(self, magnet, clientsocket, output_name=None):
        tempdir = tempfile.mkdtemp()
        ses = lt.session()
        params = {
            'save_path': tempdir,
            'storage_mode': lt.storage_mode_t(2),
            'paused': False,
            'auto_managed': True,
            'duplicate_is_error': True
        }
        handle = lt.add_magnet_uri(ses, magnet, params)

        self.send(clientsocket, "Downloading Metadata (this may take a while)")
        while (not handle.has_metadata()):
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                ses.pause()
                shutil.rmtree(tempdir)
                sys.exit(0)
        ses.pause()
        self.send(clientsocket, "Metadata finished")

        torinfo = handle.get_torrent_info()
        torfile = lt.create_torrent(torinfo)

        output = pt.abspath(torinfo.name() + ".torrent")

        if output_name:
            if pt.isdir(output_name):
                output = pt.abspath(pt.join(
                    output_name, torinfo.name() + ".torrent"))
            elif pt.isdir(pt.dirname(pt.abspath(output_name))):
                output = pt.abspath(output_name)

        self.send(clientsocket, "Saving torrent file here " + output + " ...")
        torcontent = lt.bencode(torfile.generate())
        f = open(output, "wb")
        f.write(lt.bencode(torfile.generate()))
        f.close()
        self.send(clientsocket, "Saved! Cleaning up dir: " + tempdir)

        ses.remove_torrent(handle)
        shutil.rmtree(tempdir)
        return output
    
    def download(self, file, clientsocket):
        print("downloading")
        ses = lt.session()
        ses.listen_on(6881, 6891)

        info = lt.torrent_info(file)
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
            self.send(clientsocket, report)
            time.sleep(1)

        self.send(clientsocket, "Done!")
        time.sleep(3)


serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
serversocket.bind(('', 9999))
serversocket.listen(5)

while True:
    try:
        print("waiting for connection..")
        (clientsocket, port) = serversocket.accept()
        print("found one, starting now..")

        torrent = Torrent()
        message = clientsocket.recv(1024)

        t = threading.Thread( target=torrent.start, args=(clientsocket, message) )
        t.start()
    except KeyboardInterrupt:
        clientsocket.close()
        break
