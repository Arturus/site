
from PIL import Image
import argparse
from pathlib import Path

parser = argparse.ArgumentParser(description='Prepares images for publication')
parser.add_argument('dir', help='directory where to look for images')
args = parser.parse_args()
folder = Path(args.dir)
print(folder.absolute())
for file in folder.glob("*@2x.png"):
#for file in folder.glob("*"):
  print(file)
  im = Image.open(file)
  width, height = im.size
  stem = file.stem[:-3]
  new_name = f"{stem}{file.suffix}"
  file2 = file.with_name(new_name)
  im2 = Image.open(file2)
  width2, height2 = im2.size
  print(width, height, width2, height2)
  assert width == width2 * 2
  assert height == height2 * 2
  # do_resize = False
  # if width % 2 > 0:
  #   width = width - 1
  #   do_resize = True
  # if height % 2 > 0:
  #   height = height - 1
  #   do_resize = True
  # if do_resize:
  #   im = im.crop((0, 0, width, height))
  #   im.save(file)
  # small_img = im.resize((width//2, height//2), Image.BICUBIC)
  # stem = file.stem[:-3]
  # new_name = f"{stem}{file.suffix}"
  # small_img.save(file.with_name(new_name))
  # lr_name = f"{stem}_lr{file.suffix}"
  # lr_img = im.resize((width//8, height//8), Image.BICUBIC).quantize(method=2)
  # lr_img.save(file.with_name(lr_name))
  print('{{< img src="%s" type="%s" width="%d" height="%d" >}}' % (stem, file.suffix[1:], width//2, height//2))

