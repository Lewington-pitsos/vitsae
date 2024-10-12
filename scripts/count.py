import os
from PIL import Image

# Function to check if a file is a valid image
def is_image(file_path):
    try:
        with Image.open(file_path) as img:
            img.verify()  # Check if the image is valid
        return True
    except Exception:
        return False

# Function to recursively count images in a directory
def count_images_in_directory(directory_path):
    image_count = 0
    for root, _, files in os.walk(directory_path):
        for file in files:
            file_path = os.path.join(root, file)
            if is_image(file_path):
                image_count += 1
    return image_count

# Function to count images in each subdirectory
def count_images_in_subdirectories(parent_directory):
    subdirectories = [os.path.join(parent_directory, d) for d in os.listdir(parent_directory) if os.path.isdir(os.path.join(parent_directory, d))]
    
    image_counts = {}
    
    for subdir in subdirectories:
        image_counts[subdir] = count_images_in_directory(subdir)
    
    return image_counts

# Example usage
parent_directory = 'cruft/top9'  # Change this to your directory
image_counts = count_images_in_subdirectories(parent_directory)

# Print the results
for subdir, count in image_counts.items():
    print(f"{subdir}: {count} images")


# cruft/top9/layer_2_resid: 10 images
# cruft/top9/layer_14_resid: 460 images
# cruft/top9/layer_11_resid: 240 images
# cruft/top9/layer_17_resid: 550 images
# cruft/top9/layer_5_resid: 30 images
# cruft/top9/layer_20_resid: 540 images
# cruft/top9/layer_22_resid: 1020 images
# cruft/top9/layer_8_resid: 30 images