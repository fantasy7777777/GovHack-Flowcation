import osmnx as ox
from shapely.geometry import box
import matplotlib.pyplot as plt

# Define bounding box for Parkville (rough coords, adjust if needed)
north, south, east, west = -37.77, -37.84, 145.02, 144.91
bbox_poly = box(west, south, east, north)

# Get polygon for greater Melbourne
gdf_melb = ox.geocode_to_gdf("Melbourne, Victoria, Australia")

# Get polygon for Parkville
gdf_parkville = ox.geocode_to_gdf("Parkville, Victoria, Australia")

# Plot Melbourne outline, Parkville outline, and Parkville bounding box
fig, ax = plt.subplots(figsize=(8, 8))
gdf_melb.plot(ax=ax, facecolor="none", edgecolor="red", linewidth=1, label="Melbourne")
gdf_parkville.plot(ax=ax, facecolor="none", edgecolor="green", linewidth=1, label="Parkville")
ax.plot(*bbox_poly.exterior.xy, color="blue", linewidth=2, label="Parkville BBox")

plt.title("Parkville bounding box inside Melbourne")
plt.legend()
plt.show()
