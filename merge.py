import pyvips
import os, re, time, sys
import logging, warnings
import numpy as np
from openslide import OpenSlide
import tifffile


# Setup warnings and logging
warnings.filterwarnings("ignore")

if logging.getLogger().hasHandlers():
    logging.getLogger().handlers.clear()

def mergeImages(file_id_name, width, height):
    start_time = time.time()

    # Directories containing your image tiles
    dir1 = f"./uploads/{file_id_name}/blank/"
    dir2 = f"./uploads/{file_id_name}/overlay/"

    # Function to load and store tiles with coordinates
    def load_tiles_from_directory(directory):
        tiles = []
        tile_size = None

        for filename in os.listdir(directory):
            if filename.endswith(".png"):
                match = re.search(r'(\d+)_(\d+)\.png$', filename)
                if match:
                    x, y = map(int, match.groups())
                    img = pyvips.Image.new_from_file(os.path.join(directory, filename))
                    if tile_size is None:
                        tile_size = img.width, img.height
                    tiles.append((x, y, img))

        return tiles, tile_size

    # Load tiles from both directories
    tiles1, tile_size1 = load_tiles_from_directory(dir1)
    tiles2, tile_size2 = load_tiles_from_directory(dir2)

    # Combine tiles from both directories
    all_tiles = tiles1 + tiles2
    tile_size = tile_size1 if tile_size1 else tile_size2
    print(f"Tile size of {file_id_name}: ", tile_size)

    # Sort tiles by their coordinates
    all_tiles.sort(key=lambda t: (t[1], t[0]))

    # Determine the size of the full image
    min_x = min(x for x, y, img in all_tiles)
    min_y = min(y for x, y, img in all_tiles)
    max_x = max(x for x, y, img in all_tiles)
    max_y = max(y for x, y, img in all_tiles)

    full_image_width = max_x - min_x + tile_size[0]
    full_image_height = max_y - min_y + tile_size[1]
    print("Full image width: ", full_image_width)
    print("Full image height: ", full_image_height)


    # Create a blank image
    full_image = pyvips.Image.black(full_image_width, full_image_height)

    # Composite each tile into the correct position
    for x, y, img in all_tiles:
        left = x - min_x
        top = y - min_y
        full_image = full_image.insert(img, left, top)
        
    full_image.write_to_file(f"./uploads/{file_id_name}/merged_temp_{file_id_name}.png", Q=85)

    full_image = pyvips.Image.new_from_file(f"./uploads/{file_id_name}/merged_temp_{file_id_name}.png", access="sequential")

    # Define the crop area (left, top, width, height)
    left = 0  # Starting x-coordinate
    top = 0   # Starting y-coordinate
    crop_width = width #int(input(f"Enter x dimension for {file_id}: "))
    crop_height = height #int(input(f"Enter y dimension for {file_id}: "))

    # Crop the image
    cropped_image = full_image.crop(left, top, crop_width, crop_height)

    # Resize the cropped image by 10% of its original dimensions
    resized_image = cropped_image.resize(0.1)

    # Save the final merged image
    resized_image.write_to_file(f"./uploads/{file_id_name}/Merge_{file_id_name}.png", Q=85)

    # Remove temp file to free space
    os.remove(f"./uploads/{file_id_name}/merged_temp_{file_id_name}.png")
    print("Temp file removed")

    print(f"Image segmentation and merging of {file_id_name} completed.")
    elapsed_time = time.time() - start_time
    minutes = int(elapsed_time //60)
    seconds = int(elapsed_time % 60)
    print(f"Elapsed time: {minutes} minutes {seconds} seconds")
    
    return

def main(file_path):
    norm_method = "Vaha"
    filename = os.path.basename(file_path)
    file_id = os.path.splitext(filename)[0]
    file_id_name = f"{file_id}_{norm_method}"

    if file_path.endswith('.svs') or file_path.endswith('.tif'):
        slide = OpenSlide(file_path)
        width, height = slide.level_dimensions[0]

    elif file_path.endswith('.bif'):
        with tifffile.TiffFile(file_path) as tif:
            slide_array = tif.pages[2].asarray()
            height, width = slide_array.shape[:2]
    else:
        raise ValueError("Unsupported file type")

    #create log file
    time_log_path = f"./uploads/{file_id_name}/merge-log.txt"
    os.makedirs(os.path.dirname(time_log_path), exist_ok=True)

    with open(time_log_path, 'a') as time_log_file:
        start_time = time.time()
        try:
            result = mergeImages(file_id_name, width, height)
            if result:
                elapsed_time = time.time() - start_time
                minutes = int(elapsed_time // 60)
                seconds = int(elapsed_time % 60)
                
                logging.info(f"Completed merging overlay images for file id: {result}")
                
                time_log_file.write(f"File ID: {file_id_name}, Start Time: {time.ctime(start_time)}, "
                                    f"Elapsed Time: {minutes} minutes {seconds} seconds\n")
            else:
                time_log_file.write(f"File ID: {file_id_name}, Processing Failed\n")
        except Exception as exc:
            logging.error(f"File id {file_id_name} generated an exception: {exc}")
                # Record the exception in the time log file
            time_log_file.write(f"File ID: {file_id_name}, Exception: {exc}\n")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python merge.py <filepath>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    main(file_path)