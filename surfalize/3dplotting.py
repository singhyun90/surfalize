import numpy as np
import pyvista as pv
from surfalize import Surface

path = r"C:\Users\Frederic\Desktop\test\example_150X.vk4"
surface = Surface.load(path)

off_screen=False


# Replace this with your own 2D array of height values
height_map = surface.data * 40

# Create a mesh using PyVista
grid = pv.StructuredGrid()
grid.points = np.c_[np.repeat(np.arange(height_map.shape[0]), height_map.shape[1]),
                   np.tile(np.arange(height_map.shape[1]), height_map.shape[0]),
                   height_map.flatten()]

# Reshape the array to define the mesh structure
grid.dimensions = (height_map.shape[1], height_map.shape[0], 1)

# Create a plotter
plotter = pv.Plotter(off_screen=off_screen)



#plotter.camera_position = [(10, 10, 10), (0, 0, 0), (0, 0, 1)]

# # Set a custom position and size
# sargs = dict(height=0.25, vertical=True, position_x=0.05, position_y=0.05)

kwargs = dict(diffuse=0.5, specular=0, ambient=0.5)
# Add the grid to the plotter
mesh = plotter.add_mesh(grid, scalars=height_map.flatten(), cmap="jet", show_scalar_bar=False, **kwargs)

actor = plotter.show_bounds(
    grid='back',
    location='outer',
    ticks='both',
    n_xlabels=2,
    n_ylabels=2,
    n_zlabels=2,
    xtitle='x [µm]',
    ytitle='y [µm]',
    ztitle='z [µm]',
    use_3d_text=False,
    padding=0.1,
    bold=False,
    font_size=8,
    axes_ranges=[0, surface.height_um, 0, surface.width_um, surface.data.min(), surface.data.max()]
)

# Add a vertical colorbar
plotter.add_scalar_bar(title="Height", vertical=True)
#plotter.screenshot('test.png')

# Show the plot
plotter.show()
