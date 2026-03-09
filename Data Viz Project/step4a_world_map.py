import geopandas as gpd

world = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
print(world.shape)
print(world.columns)
print(world.head(3)[["name", "iso_a3"]])
