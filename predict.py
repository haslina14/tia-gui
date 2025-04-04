import logging, warnings
import cv2
import joblib
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import os, glob, time, re, sys
import csv
import pyvips
from openslide import OpenSlide
from tiatoolbox import logger
from tiatoolbox.models.engine.nucleus_instance_segmentor import NucleusInstanceSegmentor
from tiatoolbox.utils.misc import imread
from tiatoolbox.utils.visualization import overlay_prediction_contours
from natsort import natsorted
from collections import Counter


if logging.getLogger().hasHandlers():
    logging.getLogger().handlers.clear()

logging.basicConfig(level=logging.INFO)

def predict(file_id_name):
    """Run the prediction for a given file_id and normalization method."""
    full_id = file_id_name
    logging.info(f"Processing file id: {full_id}")
    
    tile_dir = f"./uploads/{full_id}/cell/"
    save_dir_base = f"./uploads/{full_id}/result/"

    tile_paths = glob.glob(os.path.join(tile_dir, "*.png"))
    tile_paths = natsorted(tile_paths)

    if not tile_paths:
        logging.warning(f"No tiles found for file id: {full_id}")
        return

    # Record start time
    start_time = time.time()

    try:
        # Initialize the segmentor
        inst_segmentor = NucleusInstanceSegmentor(
            pretrained_model="hovernet_fast-monusac",
            num_loader_workers=2,
            num_postproc_workers=2,
            batch_size=4,
        )

        # Perform segmentation on the tile
        inst_segmentor.predict(tile_paths, save_dir=save_dir_base, mode="tile", device='cuda', crash_on_exception=True)
        
        # Log checkpoint timer
        elapsed_time = time.time() - start_time
        minutes = int(elapsed_time // 60)
        seconds = int(elapsed_time % 60)
        logging.info(f"Prediction time: {minutes} minutes {seconds} seconds")
    
    except Exception as e:
        logging.error(f"Error processing file id {full_id}: {e}")
        return None

    logging.info(f"Finished processing file id: {full_id}")
    return full_id

def cellsCount(file_id_name):

    ## Overlay image making
    # Load each .dat file collect class count and overlay the image 
    dat_dir = f"./uploads/{file_id_name}/result/"  # Directory containing the .dat files
    overlaid_dir = f"./uploads/{file_id_name}/overlay/" 

    os.makedirs(overlaid_dir, exist_ok=True)
    dat_paths = natsorted(glob.glob(os.path.join(dat_dir, "*.dat")))

    tile_dir = f"./uploads/{file_id_name}/cell/"
    csv_file_path = f"./uploads/{file_id_name}/nucleus_info_{file_id_name}.csv"  # Path for the CSV file

    tile_paths = glob.glob(os.path.join(tile_dir, "*.png"))
    sorted_tile_paths = natsorted(tile_paths)
    tile_paths = sorted_tile_paths

    start_time = time.time()

    total_counts = Counter()

    ## Open CSV file to record nucleus counts
    with open(csv_file_path, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Tile", "Dat File", "Epithelial", "Lymphocyte", "Macrophage", "Neutrophil"])
        
        # Loop through all .dat files in the directory
        for i in range(len(tile_paths)):
            # Load the predictions
            tile_preds = joblib.load(dat_paths[i])
            tile_name = os.path.splitext(os.path.basename(tile_paths[i]))[0]
            dat_name = os.path.splitext(os.path.basename(dat_paths[i]))[0]
            print(f"Tile with dat code: ", tile_name, "@", dat_name)

            # Count occurrences of each cell type
            class_counts = Counter()
            for nucleus in tile_preds.values():
                class_id = nucleus["type"]
                class_counts[class_id] += 1

            # Update the total counts with the current tile's counts            
            total_counts.update(class_counts)         
                
            # Record counts in CSV
            writer.writerow([
                tile_name,
                dat_name,
                class_counts.get(0, 0),  # Epithelial
                class_counts.get(1, 0),  # Lymphocyte
                class_counts.get(2, 0),  # Macrophage
                class_counts.get(3, 0),  # Neutrophil
            
            ])
                
            # Read the corresponding tile image for visualization
            tile_img = imread(tile_paths[i])

            # Create the overlay image
            overlaid_predictions = overlay_prediction_contours(
                canvas=tile_img,
                inst_dict=tile_preds,
                draw_dot=False,
                type_colours={
                    0: ("Epithelial", (255, 0, 0)),
                    1: ("Lymphocyte", (255, 255, 0)),
                    2: ("Macrophage", (0, 255, 0)),
                    3: ("Neutrophil", (0, 0, 255)),
                },
                line_thickness=4,    
            )
                    
            # Save the overlaid image
            overlay_path = f"./uploads/{file_id_name}/overlay/overlay_{tile_name}.png"
            plt.imsave(overlay_path, overlaid_predictions)
        
            # After all tiles are processed, write the total counts to the CSV
        writer.writerow([
            "END",
            "Total",
            total_counts.get(0, 0),  # Total Epithelial
            total_counts.get(1, 0),  # Total Lymphocyte
            total_counts.get(2, 0),  # Total Macrophage
            total_counts.get(3, 0),  # Total Neutrophil
        ])   


    # Calculate the elapsed time
    elapsed_time = time.time() - start_time
    minutes = int(elapsed_time //60)
    seconds = int(elapsed_time % 60)
    print(f"Elapsed time: {minutes} minutes {seconds} seconds")
	
    return file_id_name

def main(file_path):
    norm_method = "Vaha"
    filename = os.path.basename(file_path)
    file_id = os.path.splitext(filename)[0]
    file_id_name = f"{file_id}_{norm_method}"

    #create log file
    time_log_path = f"./uploads/{file_id_name}/predict_log.txt"
    os.makedirs(os.path.dirname(time_log_path), exist_ok=True)

    with open(time_log_path, 'a') as time_log_file:
        start_time = time.time()
        try:
            result = predict(file_id_name)
            if result:
                elapsed_time = time.time() - start_time
                minutes = int(elapsed_time // 60)
                seconds = int(elapsed_time % 60)
                
                logging.info(f"Completed processing for file id: {result}")
                
                time_log_file.write(f"File ID: {file_id_name}, Start Time: {time.ctime(start_time)}, "
                                    f"Elapsed Time: {minutes} minutes {seconds} seconds\n")
                cellsCount(file_id_name)
            else:
                time_log_file.write(f"File ID: {file_id_name}, Processing Failed\n")
        except Exception as exc:
            logging.error(f"File id {file_id_name} generated an exception: {exc}")
                # Record the exception in the time log file
            time_log_file.write(f"File ID: {file_id_name}, Exception: {exc}\n")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python predict.py <file_path> <file_name>")
    else:
        file_path = sys.argv[1]
        main(file_path)
