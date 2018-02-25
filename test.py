import libtorrent as lt
from Queue import Queue
import tempfile
import socket
import shutil
import os.path as pt
import time
import threading
import sys

class Producer:
    def __init__(self):
	    print "start Producer.." 

    def start(self, clientsocket, queue):
    	while True:
            message = clientsocket.recv(1024)
            queue.put(message) 
            if message == '0\r\n': break

class Consumer():
    def __init__(self):
        print "start Consumer.."

    def start(self, clientsocket, queue):
        while True:
            if not queue.empty():
                assigment = queue.get()
                if assigment == '0\r\n': 
                    break
                elif str.startswith(assigment, "magnet:?"):
                    torrent_file = self.convert(assigment, "torrent_tmp")
                    self.download(torrent_file, clientsocket)
                else:
                    print("got broken magnet..")
                
            print "checking queue.."
            time.sleep(1)

    def convert(self, magnet, output_name=None):
        if output_name and \
                not pt.isdir(output_name) and \
                not pt.isdir(pt.dirname(pt.abspath(output_name))):
            print("Invalid output folder: " + pt.dirname(pt.abspath(output_name)))
            print("")
            sys.exit(0)

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

        print("Downloading Metadata (this may take a while)")
        while (not handle.has_metadata()):
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                print("Aborting...")
                ses.pause()
                print("Cleanup dir " + tempdir)
                shutil.rmtree(tempdir)
                sys.exit(0)
        ses.pause()
        print("Done")

        torinfo = handle.get_torrent_info()
        torfile = lt.create_torrent(torinfo)

        output = pt.abspath(torinfo.name() + ".torrent")

        if output_name:
            if pt.isdir(output_name):
                output = pt.abspath(pt.join(
                    output_name, torinfo.name() + ".torrent"))
            elif pt.isdir(pt.dirname(pt.abspath(output_name))):
                output = pt.abspath(output_name)

        print("Saving torrent file here " + output + " ...")
        torcontent = lt.bencode(torfile.generate())
        f = open(output, "wb")
        f.write(lt.bencode(torfile.generate()))
        f.close()
        print("Saved! Cleaning up dir: " + tempdir)
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

            # print("complete: %.2f, down: %.1f kB/s, up: %.1f kB/s, peers: %d, state: %s" % \
            # (progress, d_rate, u_rate, peers_count, state),)
            report = "complete: {0} %, down: {1} kB/s, up: {2} kB/s, peers: {3}, state: {4}".format(progress, d_rate, u_rate, peers_count, state)
            clientsocket.send(report)
            time.sleep(1)

        clientsocket.send(h.name() + 'complete')
        time.sleep(3)


serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serversocket.bind(('', 9999))
serversocket.listen(5)
print("waiting for connection..")
(clientsocket, port) = serversocket.accept()
print("found one, starting now..")

producer = Producer()
consumer = Consumer()
queue = Queue()

t1 = threading.Thread( target=producer.start, args=(clientsocket, queue) )
t2 = threading.Thread( target=consumer.start, args=(clientsocket, queue) )

t1.start()
t2.start()

t1.join()
t2.join()

print "server closing.."
serversocket.close()
