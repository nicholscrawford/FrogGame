import os
import cv2
import numpy as np

from main import PLAYER_COLORS


def convert_color_space(input_folder, output_folder, target_color, target_color_name):
    # Create the output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # List all files in the input folder
    files = os.listdir(input_folder)

    for file_name in files:
        if file_name.endswith(".png") and "Frog" in file_name:
            # Read the image with alpha channel
            img_path = os.path.join(input_folder, file_name)
            img = cv2.imread(img_path, cv2.IMREAD_UNCHANGED)

            if img is not None:
                # Separate alpha channel
                alpha_channel = img[:, :, 3]

                # Convert to RGB
                img_rgb = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)

                # Convert color space to HLS (Hue, Lightness, Saturation)
                img_hls = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HLS)

                # Extract individual channels
                h, l, s = cv2.split(img_hls)

                # Convert target color to HLS
                hls_target = cv2.cvtColor(
                    np.uint8([[target_color]]), cv2.COLOR_RGB2HLS
                )[0][0]
                target_hue = hls_target[0]

                # Adjust hue and scale lightness
                hue_diff = 44 - target_hue
                h = np.mod(h + hue_diff, 180).astype(
                    np.uint8
                )  # Ensure hue stays within [0, 180]
                l = np.clip(l * (hls_target[1] / 105), 0, 255).astype(
                    np.uint8
                )  # Scale lightness
                s = np.clip(s * (hls_target[2] / 255), 0, 255).astype(np.uint8)

                # Merge channels
                img_hls = cv2.merge((h, l, s))

                # Convert back to RGB
                converted_img_rgb = cv2.cvtColor(img_hls, cv2.COLOR_HLS2RGB)

                # Combine with alpha channel
                converted_img_rgba = cv2.cvtColor(converted_img_rgb, cv2.COLOR_RGB2RGBA)
                converted_img_rgba[:, :, 3] = alpha_channel

                # Append color name to the end of the file name
                file_name = file_name.split(".")[0] + f"{target_color_name}.png"

                # Write the converted image to the output folder
                output_path = os.path.join(output_folder, file_name)
                cv2.imwrite(output_path, converted_img_rgba)


# Input and output folders
input_folder = "imgs"
output_folder = "color_rotated_imgs"

# Target color (in RGB format)
target_color = [102, 51, 153]  # Example: purple color

# Convert color space for images in the input folder and save to output folder
for color_name, color_rgb in PLAYER_COLORS.items():
    convert_color_space(input_folder, output_folder, color_rgb, color_name)
