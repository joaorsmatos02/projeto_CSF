from PIL import Image

# Function to extract the five least significant bits
def extract_five_lsb(value):
    bin_str = bin(value)[2:].zfill(8)
    return bin_str[-5:]

try:
    # Load the PNG image
    image = Image.open("logo.png")

    # Check if the image is not None
    if image is not None:
        width, height = image.size

        # Create a list to store the binary data
        binary_data = []

        # Iterate through the pixels of the image
        for y in range(1373):
            for x in range(width):
                # Based on the last modified pixel
                if not (x > 30 and y == 1372):
                    pixel = image.getpixel((x, y))

                    # Extract the RGB components
                    red, green, blue = pixel[:3]

                    # Check if is the blue component
                    if not(red == 0 and green == 159 and blue == 227):
                        # Append the five LSBs of each color component to the binary data list
                        binary_data.extend([extract_five_lsb(red), extract_five_lsb(green), extract_five_lsb(blue)])

        # Convert the binary list to bytes
        binary_string = ''.join(binary_data)
        byte_array = bytearray(int(binary_string[i:i+8], 2) for i in range(0, len(binary_string), 8))

        # Write the binary data to a file
        with open("logo.pdf", "wb") as output:
            output.write(byte_array)
    else:
        print("Failed to load the image.")
except Exception as e:
    print(e)
