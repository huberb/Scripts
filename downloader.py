import libtorrent as lt
import time
import sys

def download(file_path):
    print("downloading")
    ses = lt.session()
    ses.listen_on(6881, 6891)

    info = lt.torrent_info(file_path)
    h = ses.add_torrent({'ti': info, 'save_path': './downloads/'})

    while (not h.is_seed()):
        s = h.status()
        state_str = ['queued', 'checking', 'downloading metadata', \
            'downloading', 'finished', 'seeding', 'allocating', 'checking fastresume']
        print('%.2f%% complete (down: %.1f kb/s up: %.1f kB/s peers: %d) %s' % \
            (s.progress * 100, s.download_rate / 1000, s.upload_rate / 1000, \
            s.num_peers, state_str[s.state]),)
        sys.stdout.flush()
        time.sleep(1)

    print(h.name(), 'complete')
    time.sleep(3)

if __name__ == "__main__":
    download(sys.argv[1]);
