import rasterio
from rasterio.enums import Resampling
import matplotlib.pyplot as plt

# File path to the large image
image_path = r"C:\Users\Surafel\Desktop\bvlos_docker\Atlanta.tif"

# Open the geotagged image with Rasterio
with rasterio.open(image_path) as src:
    print(f"Original Dimensions: {src.width}x{src.height}")

    # Downscale factor (e.g., scale by 0.5 for half size)
    scale_factor = 0.5

    # Calculate new dimensions
    new_width = int(src.width * scale_factor)
    new_height = int(src.height * scale_factor)
    print(f"Scaled Dimensions: {new_width}x{new_height}")

    # Read and resample the image
    scaled_image = src.read(
        out_shape=(
            src.count,  # Number of bands (unchanged)
            new_height,  # Scaled height
            new_width,   # Scaled width
        ),
        resampling=Resampling.bilinear,  # Use bilinear interpolation for downscaling
    )

    # Adjust transform to the new dimensions
    scaled_transform = src.transform * src.transform.scale(
        (src.width / new_width), (src.height / new_height)
    )

# Display the scaled-down map
plt.imshow(scaled_image.transpose(1, 2, 0))  # Transpose to match (rows, cols, bands)
plt.axis('off')
plt.title(f"Scaled Map ({scale_factor * 100:.0f}% of Original)")
plt.show()
