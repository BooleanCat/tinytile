import zipfile
import os
import sys
import shutil
import tarfile
import tempfile

from tinifyrelease import TinifyRelease

class TinifyTile:
    def __init__(self, tile_path):
        self.tile_path = tile_path

    def tinify(self, tiny_tile_path):
        try:
            temp_dir = tempfile.mkdtemp()
            self._tinify(tiny_tile_path, temp_dir)
        finally:
            if os.path.isdir(temp_dir):
                shutil.rmtree(temp_dir)

    def _tinify(self, tiny_tile_path, temp_dir):
        with zipfile.ZipFile(self.tile_path) as zip_ref:
            print('unzipping tile: {}'.format(self.tile_path))
            zip_ref.extractall(temp_dir)

        releases = os.listdir(os.path.join(temp_dir, 'releases'))
        releases_paths = [os.path.join(temp_dir, 'releases', release) for release in releases]

        for release in releases_paths:
            if not TinifyRelease.is_compiled_release(release):
                continue

            tinify_release = TinifyRelease(release)
            print('tinifying release: {}'.format(os.path.basename(release)))
            tinify_release.tinify(release + '.tiny')
            os.remove(release)
            os.rename(release + '.tiny', release)

        shutil.make_archive(tiny_tile_path, 'zip', root_dir=temp_dir)
        os.rename(tiny_tile_path + '.zip', tiny_tile_path)


def main():
    tile_path = sys.argv[1]
    tiny_tile_path = sys.argv[2]

    initial_size = os.path.getsize(tile_path)
    print('input file size {} MB: '.format(initial_size >> 20))

    tinify_tile = TinifyTile(tile_path)
    tinify_tile.tinify(tiny_tile_path)

    final_size = os.path.getsize(tiny_tile_path)
    print('output file size: {} MB'.format(final_size >> 20))
    print('{0:.2f}% reduction!'.format(100 - 100 * float(final_size) / initial_size))

if __name__ == '__main__':
    main()
