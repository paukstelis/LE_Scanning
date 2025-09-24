import numpy as np
from stl import mesh
import math

class STLGenerator:
    def __init__(self, coords, start_diameter, num_segments=96):
        """
        Initialize the STLGenerator with coordinates, starting diameter, and number of segments.
        
        Parameters:
        coords (list of tuples): List of (X, Z) coordinates.
        start_diameter (float): Diameter at the first Z coordinate.
        num_segments (int): Number of segments to approximate circles in the STL mesh.
        """
        # Convert coordinates to a numpy array
        self.coords = np.array(coords, dtype=np.float32)
        self.start_diameter = start_diameter
        self.num_segments = num_segments

        # Zero the coordinates based on the first point
        self._zero_coordinates()

    def _zero_coordinates(self):
        """Zero the X and Z coordinates based on the first coordinate."""
        x0, z0, a0 = self.coords[0]
        self.coords[:, 0] -= x0  # Adjust X values
        self.coords[:, 1] -= z0  # Adjust Z values to zero

        # Adjust the Z values (radii) to reflect the starting diameter
        initial_radius = self.start_diameter / 2
        radius_offset = initial_radius - self.coords[0, 1]
        self.coords[:, 1] += radius_offset  # Directly adjust radii by adding the offset

    def generate_mesh(self):
        """Generate vertices and faces for the STL mesh."""
        vertices = []
        faces = []

        for i, (x, radius) in enumerate(self.coords):
            angle_step = 2 * np.pi / self.num_segments
            circle_points = [
                (x, radius * math.cos(angle), radius * math.sin(angle))
                for angle in np.arange(0, 2 * np.pi, angle_step)
            ]
            vertices.extend(circle_points)

            # Create faces by connecting the current circle with the previous one
            if i > 0:
                start_index = (i - 1) * self.num_segments
                for j in range(self.num_segments):
                    next_j = (j + 1) % self.num_segments
                    face1 = [start_index + j, start_index + j + self.num_segments, start_index + next_j + self.num_segments]
                    face2 = [start_index + j, start_index + next_j + self.num_segments, start_index + next_j]
                    faces.append(face1)
                    faces.append(face2)

        # Convert to numpy arrays
        self.vertices = np.array(vertices)
        self.faces = np.array(faces)

    def save_stl(self, output_file="output.stl"):
        """Save the generated mesh as an STL file."""
        # Create the mesh
        stl_mesh = mesh.Mesh(np.zeros(self.faces.shape[0], dtype=mesh.Mesh.dtype))
        for i, face in enumerate(self.faces):
            for j in range(3):
                stl_mesh.vectors[i][j] = self.vertices[face[j], :]

        # Write to STL file
        stl_mesh.save(output_file)
        #print(f"STL file saved as {output_file}")